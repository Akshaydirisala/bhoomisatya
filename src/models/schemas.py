from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# --- Enums ---


class StateEnum(str, Enum):
    telangana = "telangana"
    andhra_pradesh = "andhra_pradesh"


class ReportType(str, Enum):
    quick_check = "quick_check"
    full_report = "full_report"
    premium_report = "premium_report"


class SafetyVerdictEnum(str, Enum):
    safe = "safe"
    caution = "caution"
    unsafe = "unsafe"


class ValuationVerdictEnum(str, Enum):
    fair_price = "fair_price"
    overpriced = "overpriced"
    underpriced = "underpriced"
    insufficient_data = "insufficient_data"


class ReportStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SeverityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# --- Input / Output schemas ---


class PropertyInput(BaseModel):
    survey_number: str
    district: str
    mandal: str
    village: str
    state: StateEnum
    asking_price: Decimal | None = None
    asking_price_unit: str | None = None


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trust_score: int | None = None
    safety_verdict: SafetyVerdictEnum | None = None
    valuation_verdict: ValuationVerdictEnum | None = None
    guideline_value: Decimal | None = None
    market_value_range: dict | None = None
    status: ReportStatusEnum
    pdf_url: str | None = None
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


# --- WhatsApp Webhook ---


class WhatsAppProfile(BaseModel):
    name: str


class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile
    wa_id: str


class WhatsAppText(BaseModel):
    body: str


class WhatsAppMessage(BaseModel):
    from_: str | None = None
    id: str
    timestamp: str
    text: WhatsAppText | None = None
    type: str

    model_config = ConfigDict(populate_by_name=True)


class WhatsAppMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: list[WhatsAppContact] | None = None
    messages: list[WhatsAppMessage] | None = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WhatsAppEntry]


# --- Scraped data schemas ---


class LandRecord(BaseModel):
    owner_name: str
    survey_number: str
    extent: Decimal
    extent_unit: str
    land_type: str
    mutation_history: list[dict] = []


class RERAProject(BaseModel):
    project_name: str
    rera_number: str
    promoter: str
    status: str
    registered_date: str | None = None
    expiry_date: str | None = None


class CourtCase(BaseModel):
    case_number: str
    parties: str
    court: str
    status: str
    filing_date: str | None = None
    case_type: str | None = None


class EncumbranceRecord(BaseModel):
    document_number: str
    document_type: str
    parties: str
    registration_date: str | None = None
    sro_name: str | None = None


class ComparableSale(BaseModel):
    survey_number: str
    village: str
    extent: Decimal
    sale_value: Decimal
    registration_date: str | None = None
    distance_km: float | None = None


class ValuationData(BaseModel):
    guideline_value_per_unit: Decimal
    unit: str
    comparable_sales: list[ComparableSale] = []
    estimated_market_value_low: Decimal | None = None
    estimated_market_value_high: Decimal | None = None


# --- Analysis result schemas ---


class Finding(BaseModel):
    category: str
    severity: SeverityEnum
    description: str
    source: str


class SafetyAnalysis(BaseModel):
    trust_score: int
    verdict: SafetyVerdictEnum
    findings: list[Finding] = []


class ValuationAnalysis(BaseModel):
    verdict: ValuationVerdictEnum
    guideline_value: Decimal | None = None
    market_range_low: Decimal | None = None
    market_range_high: Decimal | None = None
    reasoning: str
    comparable_count: int = 0
