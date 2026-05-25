"""Razorpay payment integration for BhoomiSatya."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class RazorpayClient:
    """Async client for Razorpay Payment Links and webhook handling."""

    def __init__(
        self,
        key_id: str,
        key_secret: str,
        webhook_secret: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._key_id = key_id
        self._key_secret = key_secret
        self._webhook_secret = webhook_secret
        self._timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            auth=(self._key_id, self._key_secret),
            timeout=self._timeout,
        )

    async def create_payment_link(
        self,
        amount_paise: int,
        report_id: str,
        phone: str,
        description: str,
    ) -> dict[str, Any]:
        """Create a Razorpay Payment Link.

        Args:
            amount_paise: Amount in paise (e.g. 49900 for ₹499).
            report_id: BhoomiSatya report ID for reference.
            phone: Customer phone number (for SMS/WhatsApp delivery).
            description: Payment description text.

        Returns:
            Dict with 'id', 'short_url', 'status', and 'amount'.

        Raises:
            httpx.HTTPStatusError: On API error.
        """
        log = logger.bind(action="create_payment_link", report_id=report_id, amount=amount_paise)
        log.info("creating_payment_link")

        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "description": description,
            "reference_id": report_id,
            "customer": {
                "contact": phone,
            },
            "notify": {
                "sms": True,
                "whatsapp": True,
            },
            "callback_url": "",  # Set via env/config in production
            "callback_method": "get",
            "notes": {
                "report_id": report_id,
                "source": "bhoomisatya",
            },
        }

        async with self._client() as client:
            resp = await client.post(f"{RAZORPAY_API_BASE}/payment_links", json=payload)
            resp.raise_for_status()

        data = resp.json()
        log.info("payment_link_created", link_id=data.get("id"), short_url=data.get("short_url"))

        return {
            "id": data["id"],
            "short_url": data["short_url"],
            "status": data.get("status"),
            "amount": data.get("amount"),
        }

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify Razorpay webhook signature.

        Args:
            body: Raw request body bytes.
            signature: Value of the X-Razorpay-Signature header.

        Returns:
            True if the signature is valid.
        """
        expected = hmac.new(
            self._webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        valid = hmac.compare_digest(expected, signature)
        if not valid:
            logger.warning("invalid_razorpay_webhook_signature")
        return valid

    async def handle_payment_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a Razorpay payment webhook event.

        Args:
            payload: Parsed JSON webhook body from Razorpay.

        Returns:
            Dict with payment_id, payment_link_id, report_id, status,
            and amount.
        """
        log = logger.bind(action="handle_payment_webhook")

        event = payload.get("event", "")
        entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})

        result = {
            "event": event,
            "payment_link_id": entity.get("id"),
            "report_id": entity.get("reference_id") or entity.get("notes", {}).get("report_id"),
            "payment_id": payment.get("id"),
            "status": entity.get("status") or payment.get("status"),
            "amount": entity.get("amount") or payment.get("amount"),
        }

        log.info("webhook_processed", **result)
        return result
