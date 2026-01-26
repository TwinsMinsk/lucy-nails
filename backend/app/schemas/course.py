"""
Pydantic схемы для курсов.
"""

from uuid import UUID
from pydantic import BaseModel, Field


class CourseBase(BaseModel):
    """Базовая схема курса."""
    
    title: str = Field(..., description="Название курса")
    description: str | None = Field(None, description="Описание курса")
    preview_video_url: str | None = Field(None, description="URL превью видео")
    cover_image_url: str | None = Field(None, description="URL обложки")
    price_self: int = Field(..., description="Цена тарифа 'Самостоятельный' (в рублях)")
    price_support: int = Field(..., description="Цена тарифа 'С поддержкой' (в рублях)")


class CourseResponse(CourseBase):
    """Схема ответа с данными курса."""
    
    id: UUID = Field(..., description="UUID курса")
    is_published: bool = Field(..., description="Опубликован ли курс")
    modules_count: int | None = Field(None, description="Количество модулей")
    lessons_count: int | None = Field(None, description="Количество уроков")
    total_duration: int | None = Field(None, description="Общая длительность (секунды)")
    
    class Config:
        from_attributes = True
        use_enum_values = True


class CourseListResponse(BaseModel):
    """Схема списка курсов."""
    
    courses: list[CourseResponse]
    total: int = Field(..., description="Общее количество курсов")
