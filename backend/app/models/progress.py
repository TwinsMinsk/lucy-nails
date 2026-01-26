"""
Модель прогресса прохождения урока (Progress).
"""

import uuid
from datetime import datetime

from sqlalchemy import Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Progress(Base):
    """Прогресс просмотра уроков пользователями."""
    
    __tablename__ = "progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    watched_seconds: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="progress")
    lesson: Mapped["Lesson"] = relationship(back_populates="progress")
    
    def __repr__(self) -> str:
        return f"<Progress user={self.user_id} lesson={self.lesson_id} ({self.watched_seconds}s)>"
