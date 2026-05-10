"""
Модель модуля/блока курса (Module).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Module(Base):
    """Блоки (модули) курса, группирующие уроки по темам."""

    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Landing copy overrides. NULL → frontend falls back to course-content.ts (matched by Module.title slug).
    landing_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    landing_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    landing_bullets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    landing_mistakes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    landing_duration_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    # Relationships
    course: Mapped["Course"] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order_index")
    
    def __repr__(self) -> str:
        return f"<Module {self.title} (order: {self.order_index})>"
