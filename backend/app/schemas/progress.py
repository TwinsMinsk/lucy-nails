"""
Pydantic схемы для прогресса прохождения уроков.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProgressBase(BaseModel):
    """Базовая схема прогресса."""
    
    watched_seconds: int = Field(0, description="Просмотренное время в секундах")
    is_completed: bool = Field(False, description="Просмотрен ли урок полностью")


class ProgressUpdate(ProgressBase):
    """Схема для обновления прогресса."""
    pass


class ProgressResponse(ProgressBase):
    """Схема ответа с данными прогресса."""
    
    id: UUID = Field(..., description="UUID записи прогресса")
    user_id: UUID = Field(..., description="UUID пользователя")
    lesson_id: UUID = Field(..., description="UUID урока")
    completed_at: datetime | None = Field(None, description="Дата завершения")
    updated_at: datetime = Field(..., description="Дата последнего обновления")
    
    class Config:
        from_attributes = True
