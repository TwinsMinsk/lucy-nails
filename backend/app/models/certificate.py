"""
Модель сертификата (Certificate).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Certificate(Base):
    """Выданные сертификаты о прохождении курсов."""

    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_certificates_user_course"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    certificate_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(512))
    png_url: Mapped[str | None] = mapped_column(String(512))
    issued_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="certificates", foreign_keys=[user_id])
    course: Mapped["Course"] = relationship(back_populates="certificates")
    revoked_by: Mapped["User | None"] = relationship(foreign_keys=[revoked_by_id])
    
    def __repr__(self) -> str:
        return f"<Certificate {self.certificate_number}>"
