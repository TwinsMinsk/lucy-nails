"""
Модель курса (Course).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Course(Base):
    """Курсы с ценами для каждого тарифа."""

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    preview_video_url: Mapped[str | None] = mapped_column(String(512))
    cover_image_url: Mapped[str | None] = mapped_column(String(512))
    price_self: Mapped[int] = mapped_column(Integer, nullable=False)  # в рублях
    price_support: Mapped[int] = mapped_column(Integer, nullable=False)  # в рублях
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Landing hero overrides. NULL → frontend falls back to course-content.ts.
    landing_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    landing_subtitle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    landing_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    landing_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    landing_support_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    landing_hero_stats: Mapped[list | None] = mapped_column(JSON, nullable=True)
    landing_benefits: Mapped[list | None] = mapped_column(JSON, nullable=True)
    landing_instructor_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Relationships
    modules: Mapped[list["Module"]] = relationship(back_populates="course", cascade="all, delete-orphan", order_by="Module.order_index")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Course {self.title}>"
