"""
API эндпоинты для модулей.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.module import ModuleResponse
from app.schemas.lesson import LessonOutlineResponse
from app.services.module_service import ModuleService


router = APIRouter()


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить детали модуля по ID (только опубликованный модуль и курс).
    """
    module = await ModuleService.get_module_by_id(db, module_id)

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )
    if not module.is_published or not module.course or not module.course.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    stats = await ModuleService.get_module_stats(db, module_id)
    module_data = ModuleResponse.from_orm(module)
    module_data.lessons_count = stats["lessons_count"]
    module_data.total_duration = stats["total_duration"]

    return module_data


@router.get("/{module_id}/lessons", response_model=list[LessonOutlineResponse])
async def get_module_lessons(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список уроков модуля (публичный каталог без ID видео).
    """
    module = await ModuleService.get_module_by_id(db, module_id, include_lessons=True)

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )
    if not module.is_published or not module.course or not module.course.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    lessons = sorted(module.lessons, key=lambda x: x.order_index)

    return [LessonOutlineResponse.model_validate(lesson) for lesson in lessons]
