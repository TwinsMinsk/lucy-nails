"""
Pydantic схемы для уроков.
"""

from uuid import UUID
from pydantic import BaseModel, Field


class LessonBase(BaseModel):
    """Базовая схема урока."""
    
    title: str = Field(..., description="Название урока")
    description: str | None = Field(None, description="Описание урока")
    content: str | None = Field(None, description="Форматированный текст (конспект)")
    duration_seconds: int = Field(..., description="Длительность (секунды)")
    order_index: int = Field(..., description="Порядковый номер")


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
