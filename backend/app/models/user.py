"""
Модель пользователя (User).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Пользователи системы (ученики и админы)."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        SQLEnum("student", "admin", name="user_role"),
        nullable=False,
        default="student"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    progress: Mapped[list["Progress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
