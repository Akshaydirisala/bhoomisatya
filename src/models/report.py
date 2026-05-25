import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class StateEnum(str, enum.Enum):
    telangana = "telangana"
    andhra_pradesh = "andhra_pradesh"


class ReportType(str, enum.Enum):
    quick_check = "quick_check"
    full_report = "full_report"
    premium_report = "premium_report"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SafetyVerdict(str, enum.Enum):
    safe = "safe"
    caution = "caution"
    unsafe = "unsafe"


class ValuationVerdict(str, enum.Enum):
    fair_price = "fair_price"
    overpriced = "overpriced"
    underpriced = "underpriced"
    insufficient_data = "insufficient_data"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    survey_number: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(255))
    mandal: Mapped[str] = mapped_column(String(255))
    village: Mapped[str] = mapped_column(String(255))
    state: Mapped[StateEnum] = mapped_column()

    asking_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    asking_price_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    report_type: Mapped[ReportType] = mapped_column()
    status: Mapped[ReportStatus] = mapped_column(default=ReportStatus.pending)

    trust_score: Mapped[int | None] = mapped_column(nullable=True)
    safety_verdict: Mapped[SafetyVerdict | None] = mapped_column(nullable=True)
    valuation_verdict: Mapped[ValuationVerdict | None] = mapped_column(nullable=True)

    guideline_value_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    estimated_market_value_low: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    estimated_market_value_high: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.pending)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="reports")  # noqa: F821
