"""Sanitized, idempotent payment-provider event journal."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Every status the application writes: "received" while an event is being
# processed, then one terminal status. Kept equal to migration a3b4c5d6e7f8.
PAYMENT_EVENT_STATUSES = (
    "received",
    "processed",
    "duplicate",
    "ignored",
    "rejected",
    "financial_incident",
)


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        CheckConstraint(
            "processing_status IN ("
            + ", ".join(f"'{status}'" for status in PAYMENT_EVENT_STATUSES)
            + ")",
            name="ck_payment_events_processing_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="prodamus")
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    external_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    order_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount_kopecks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sanitized_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped["Order | None"] = relationship(back_populates="payment_events")
    purchase: Mapped["Purchase | None"] = relationship(back_populates="payment_events")
