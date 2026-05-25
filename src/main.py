"""BhoomiSatya API - Property verification service for Telangana & Andhra Pradesh."""

from __future__ import annotations

import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import settings
from src.database import init_db, get_db, Report, ReportStatus
from src.agent.orchestrator import run_verification_pipeline
from src.channels.whatsapp import (
    parse_whatsapp_message,
    download_media,
    send_whatsapp_message,
)
from src.language.bhashini import transcribe_audio
from src.payments.razorpay import verify_razorpay_signature, create_payment_link

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: float


class ReportRequest(BaseModel):
    """Payload accepted from web/API clients (non-WhatsApp)."""

    property_description: str = Field(..., min_length=5, max_length=2000)
    report_type: str = Field(default="full", pattern="^(quick|full|premium)$")
    phone_number: Optional[str] = None
    district: Optional[str] = None
    state: str = Field(default="telangana", pattern="^(telangana|andhra_pradesh)$")


class ReportResponse(BaseModel):
    report_id: str
    status: str
    report_type: str
    payment_status: Optional[str] = None
    result: Optional[dict] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("bhoomisatya.startup", version="0.1.0")
    await init_db()
    logger.info("bhoomisatya.database_ready")
    yield
    logger.info("bhoomisatya.shutdown")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BhoomiSatya API",
    version="0.1.0",
    description="AI-powered property verification for Telangana & Andhra Pradesh",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, "CORS_ORIGINS") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Background task: run full verification pipeline
# ---------------------------------------------------------------------------


async def process_verification(
    report_id: str,
    property_input: str,
    report_type: str,
    phone_number: Optional[str],
) -> None:
    """Run the AI orchestrator, update the DB, and deliver the report."""
    log = logger.bind(report_id=report_id)
    try:
        log.info("verification.started")
        db = await get_db()

        # Run the LangGraph verification pipeline
        result = await run_verification_pipeline(
            property_input=property_input,
            report_type=report_type,
        )

        # Persist results
        await db.update_report(
            report_id,
            status=ReportStatus.COMPLETED,
            result=result,
        )
        log.info("verification.completed")

        # If a phone number exists, send WhatsApp delivery message
        if phone_number:
            pdf_url = result.get("pdf_url", "")
            summary = result.get("summary", "Your BhoomiSatya report is ready.")
            await send_whatsapp_message(
                phone_number=phone_number,
                message=f"✅ *BhoomiSatya Report Ready*\n\n{summary}\n\n📄 Download: {pdf_url}",
            )

    except Exception:
        log.exception("verification.failed")
        db = await get_db()
        await db.update_report(report_id, status=ReportStatus.FAILED)
        if phone_number:
            await send_whatsapp_message(
                phone_number=phone_number,
                message="⚠️ Sorry, we encountered an error processing your property verification. "
                "Please try again or contact support.",
            )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", version="0.1.0", timestamp=time.time())


# -- WhatsApp webhook -------------------------------------------------------


@app.get("/api/v1/webhook/whatsapp")
async def whatsapp_verify(
    mode: str = Query(alias="hub.mode", default=""),
    token: str = Query(alias="hub.verify_token", default=""),
    challenge: str = Query(alias="hub.challenge", default=""),
):
    """Verify the WhatsApp webhook subscription."""
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("whatsapp.webhook_verified")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/api/v1/webhook/whatsapp")
async def whatsapp_receive(request: Request, background_tasks: BackgroundTasks):
    """Receive incoming WhatsApp messages and kick off verification."""
    body = await request.json()
    message = parse_whatsapp_message(body)

    if message is None:
        # Status update or unsupported message type – acknowledge silently
        return {"status": "ignored"}

    phone_number = message["from"]
    property_input = message.get("text", "")

    # If voice note, transcribe via Bhashini ASR
    if message.get("type") == "audio":
        media_url = message["audio"]["url"]
        media_id = message["audio"]["id"]
        audio_bytes = await download_media(media_id)
        property_input = await transcribe_audio(audio_bytes, language="te")
        logger.info("whatsapp.voice_transcribed", length=len(property_input))

    if not property_input:
        await send_whatsapp_message(
            phone_number=phone_number,
            message="🙏 Please describe the property you want verified — "
            "send a text or voice note in Telugu/English.",
        )
        return {"status": "prompt_sent"}

    # Create report in DB
    db = await get_db()
    report = await db.create_report(
        phone_number=phone_number,
        property_input=property_input,
        report_type="quick",
        source="whatsapp",
    )

    # Send "processing" acknowledgement
    await send_whatsapp_message(
        phone_number=phone_number,
        message="🔍 *BhoomiSatya* is verifying your property now.\n\n"
        "We'll check Dharani, RERA, encumbrances, and market value.\n"
        "You'll receive the report in a few minutes.",
    )

    # Schedule the heavy lifting
    background_tasks.add_task(
        process_verification,
        report_id=report.id,
        property_input=property_input,
        report_type="quick",
        phone_number=phone_number,
    )

    return {"status": "processing", "report_id": report.id}


# -- Razorpay webhook -------------------------------------------------------


@app.post("/api/v1/webhook/razorpay")
async def razorpay_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Razorpay payment callbacks."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_razorpay_signature(body, signature, settings.RAZORPAY_WEBHOOK_SECRET):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event", "")

    if event == "payment.captured":
        payment_entity = payload["payload"]["payment"]["entity"]
        report_id = payment_entity.get("notes", {}).get("report_id")
        if not report_id:
            logger.warning("razorpay.missing_report_id", payment_id=payment_entity["id"])
            return {"status": "ignored"}

        db = await get_db()
        report = await db.get_report(report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")

        await db.update_report(report_id, payment_status="paid")
        logger.info("razorpay.payment_captured", report_id=report_id)

        # If report is already completed, trigger delivery
        if report.status == ReportStatus.COMPLETED:
            background_tasks.add_task(
                process_verification,
                report_id=report_id,
                property_input=report.property_input,
                report_type=report.report_type,
                phone_number=report.phone_number,
            )

    return {"status": "ok"}


# -- Reports API -------------------------------------------------------------


@app.get("/api/v1/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Retrieve report status and data."""
    db = await get_db()
    report = await db.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse(
        report_id=report.id,
        status=report.status,
        report_type=report.report_type,
        payment_status=report.payment_status,
        result=report.result,
        created_at=str(report.created_at),
    )


@app.post("/api/v1/reports", response_model=ReportResponse, status_code=201)
async def create_report(req: ReportRequest, background_tasks: BackgroundTasks):
    """Create a report via API (for web/mobile clients, not WhatsApp)."""
    db = await get_db()
    report = await db.create_report(
        phone_number=req.phone_number,
        property_input=req.property_description,
        report_type=req.report_type,
        source="api",
    )

    background_tasks.add_task(
        process_verification,
        report_id=report.id,
        property_input=req.property_description,
        report_type=req.report_type,
        phone_number=req.phone_number,
    )

    return ReportResponse(
        report_id=report.id,
        status=report.status,
        report_type=report.report_type,
        created_at=str(report.created_at),
    )
