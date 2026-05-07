"""
Модель урока (Lesson).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Lesson(Base):
    """Уроки с ссылками на Kinescope, принадлежат модулю."""
    
    __tablename__ = "lessons"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kinescope_video_id: Mapped[str | None] = mapped_column(String(255))
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str | None] = mapped_column(Text)  # Форматированный текст (конспект)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_preview: Mapped[bool] = mapped_column(Boolean, default=False)  # Бесплатный превью урок
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Промо для лендинга (короткий ролик Kinescope + текст)
    promo_kinescope_video_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    promo_poster_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    promo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    promo_highlights: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Relationships
    module: Mapped["Module"] = relationship(back_populates="lessons")
    progress: Mapped[list["Progress"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Lesson {self.title} (order: {self.order_index})>"
