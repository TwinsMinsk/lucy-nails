"""
Сервис для работы с модулями.
"""

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.module import Module
from app.models.lesson import Lesson


class ModuleService:
    """Сервис для работы с модулями."""
    
    @staticmethod
    async def get_course_modules(
        db: AsyncSession, 
        course_id: UUID,
        include_lessons: bool = False
    ) -> list[Module]:
        """
        Получить модули курса.
        
        Args:
            db: Сессия БД
            course_id: UUID курса
            include_lessons: Загрузить уроки модулей
        
        Returns:
            Список модулей
        """
        query = select(Module).where(
            Module.course_id == course_id,
            Module.is_published
        ).order_by(Module.order_index)
        
        if include_lessons:
            query = query.options(selectinload(Module.lessons))
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_module_by_id(
        db: AsyncSession, 
        module_id: UUID,
        include_lessons: bool = False
    ) -> Module | None:
        """
        Получить модуль по ID.
        
        Args:
            db: Сессия БД
            module_id: UUID модуля
            include_lessons: Загрузить уроки
        
        Returns:
            Module или None
        """
        opts = [selectinload(Module.course)]
        if include_lessons:
            opts.append(selectinload(Module.lessons))
        query = select(Module).where(Module.id == module_id).options(*opts)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_module_stats(db: AsyncSession, module_id: UUID) -> dict:
        """
        Получить статистику модуля (количество уроков, общая длительность).
        
        Args:
            db: Сессия БД
            module_id: UUID модуля
        
        Returns:
            Словарь со статистикой
        """
        query = select(
            func.count(Lesson.id),
            func.sum(Lesson.duration_seconds)
        ).where(Lesson.module_id == module_id)
        
        result = await db.execute(query)
        lessons_count, total_duration = result.one()
        
        return {
            "lessons_count": lessons_count or 0,
            "total_duration": total_duration or 0
        }
