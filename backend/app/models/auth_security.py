"""MFA credentials and revocable authentication sessions."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MfaCredential(Base):
    __tablename__ = "mfa_credentials"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    backup_code_hashes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    enabled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="mfa_credential")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    user: Mapped["User"] = relationship(back_populates="auth_sessions")
