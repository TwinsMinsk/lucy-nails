"""
Модель пользователя (User).
"""

import uuid
from datetime import datetime

from sqlalchemy import Index, String, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Пользователи системы (ученики и админы)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    __table_args__ = (
        # Enforces email case-insensitivity at the DB level; lookups also use
        # func.lower(email) so legacy mixed-case rows still match.
        Index("ix_users_email_lower", func.lower(email), unique=True),
    )

    phone: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        SQLEnum("student", "admin", name="user_role"),
        nullable=False,
        default="student"
    )
    # Bumped on every password change/reset. Embedded as "ver" in issued JWTs;
    # a token whose "ver" != this value is rejected, so changing the password
    # invalidates all previously issued access/refresh/reset tokens.
    token_version: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    # Consent proof from self-registration or copied from the guest checkout order.
    offer_accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    personal_data_consent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    progress: Mapped[list["Progress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    certificates: Mapped[list["Certificate"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Certificate.user_id",
    )
    entitlements: Mapped[list["Entitlement"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Entitlement.user_id",
    )
    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserRoleAssignment.user_id",
    )
    mfa_credential: Mapped["MfaCredential | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
