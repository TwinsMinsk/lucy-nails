"""
Модель покупки (Purchase).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Purchase(Base):
    """Покупки курсов с датой истечения доступа."""
    
    __tablename__ = "purchases"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    tariff: Mapped[str] = mapped_column(
        SQLEnum("self", "support", name="tariff_type"),
        nullable=False
    )
    amount_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)  # в копейках
    payment_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    payment_status: Mapped[str] = mapped_column(
        SQLEnum("pending", "success", "failed", name="payment_status"),
        nullable=False,
        default="pending"
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="purchases")
    course: Mapped["Course"] = relationship(back_populates="purchases")
    
    def __repr__(self) -> str:
        return f"<Purchase {self.id} ({self.tariff}, {self.payment_status})>"
