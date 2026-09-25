"""Course access grants kept separately from financial purchases."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Entitlement(Base):
    """A revocable, time-bounded right to access one course."""

    __tablename__ = "entitlements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'suspended', 'revoked', 'expired')",
            name="ck_entitlements_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("purchases.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    granted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    tariff: Mapped[str] = mapped_column(String(32), nullable=False, default="self")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(
        back_populates="entitlements", foreign_keys=[user_id]
    )
    course: Mapped["Course"] = relationship(back_populates="entitlements")
    source_purchase: Mapped["Purchase | None"] = relationship(back_populates="entitlement")
    granted_by: Mapped["User | None"] = relationship(foreign_keys=[granted_by_id])
