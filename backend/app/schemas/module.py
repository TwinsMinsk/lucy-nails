"""
Pydantic схемы для модулей.
"""

from uuid import UUID
from pydantic import BaseModel, Field


class ModuleBase(BaseModel):
    """Базовая схема модуля."""
    
    title: str = Field(..., description="Название модуля")
    description: str | None = Field(None, description="Описание модуля")
    order_index: int = Field(..., description="Порядковый номер")


class ModuleResponse(ModuleBase):
    """Схема ответа с данными модуля."""
    
    id: UUID = Field(..., description="UUID модуля")
    course_id: UUID = Field(..., description="UUID курса")
    is_published: bool = Field(..., description="Опубликован ли модуль")
    lessons_count: int | None = Field(None, description="Количество уроков")
    total_duration: int | None = Field(None, description="Общая длительность (секунды)")
    
    class Config:
        from_attributes = True
        use_enum_values = True


from app.schemas.lesson import LessonResponse

class ModuleWithLessonsResponse(ModuleResponse):
    """Схема модуля со списком уроков."""
    
    lessons: list[LessonResponse] = Field(default_factory=list, description="Список уроков")

