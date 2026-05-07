"""
Pydantic схемы для уроков.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LessonBase(BaseModel):
    """Базовая схема урока."""
    
    title: str = Field(..., description="Название урока")
    description: str | None = Field(None, description="Описание урока")
    content: str | None = Field(None, description="Форматированный текст (конспект)")
    duration_seconds: int = Field(..., description="Длительность (секунды)")
    order_index: int = Field(..., description="Порядковый номер")


class LessonOutlineResponse(BaseModel):
    """Публичное описание урока без ID основного видео (каталог / превью структуры)."""

    id: UUID = Field(..., description="UUID урока")
    module_id: UUID = Field(..., description="UUID модуля")
    title: str = Field(..., description="Название урока")
    description: str | None = Field(None, description="Описание урока")
    duration_seconds: int = Field(..., description="Длительность (секунды)")
    order_index: int = Field(..., description="Порядковый номер")
    is_preview: bool = Field(..., description="Бесплатный превью урок")

    promo_kinescope_video_id: str | None = Field(None, description="ID промо-видео в Kinescope")
    promo_poster_url: str | None = Field(None, description="Постер промо")
    promo_description: str | None = Field(None, description="Краткое описание для программы курса")
    promo_bullets: list[str] = Field(default_factory=list, description="Буллеты «что узнаете»")

    class Config:
        from_attributes = True
        use_enum_values = True

    @classmethod
    def from_lesson(cls, lesson: Any) -> LessonOutlineResponse:
        """Собирает ответ с учётом JSON promo_highlights."""
        from app.models.lesson import Lesson as LessonModel

        if not isinstance(lesson, LessonModel):
            raise TypeError("Expected Lesson ORM instance")

        ph = lesson.promo_highlights if isinstance(lesson.promo_highlights, dict) else {}
        bullets = list(ph.get("bullets") or [])
        return cls(
            id=lesson.id,
            module_id=lesson.module_id,
            title=lesson.title,
            description=lesson.description,
            duration_seconds=lesson.duration_seconds,
            order_index=lesson.order_index,
            is_preview=lesson.is_preview,
            promo_kinescope_video_id=lesson.promo_kinescope_video_id,
            promo_poster_url=lesson.promo_poster_url,
            promo_description=lesson.promo_description,
            promo_bullets=bullets,
        )


class LessonResponse(LessonBase):
    """Схема ответа с данными урока."""
    
    id: UUID = Field(..., description="UUID урока")
    module_id: UUID = Field(..., description="UUID модуля")
    is_preview: bool = Field(..., description="Бесплатный превью урок")
    kinescope_video_id: str | None = Field(None, description="ID видео в Kinescope (только при наличии доступа)")
    
    class Config:
        from_attributes = True
        use_enum_values = True


class LessonDetailResponse(LessonResponse):
    """Детальная схема урока с видео."""
    
    video_url: str | None = Field(None, description="URL для просмотра видео (signed)")


class VideoPlayResponse(BaseModel):
    """Схема ответа для воспроизведения видео."""
    
    video_url: str = Field(..., description="URL для embed-плеера")
    provider: str = Field("kinescope", description="Провайдер видео")
    title: str = Field(..., description="Название урока")
    
    class Config:
        from_attributes = True
