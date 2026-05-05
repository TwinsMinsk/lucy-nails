"""
Сервис для работы с курсами.
"""

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson


class CourseService:
    """Сервис для работы с курсами."""
    
    @staticmethod
    async def get_courses(db: AsyncSession, only_published: bool = True) -> list[Course]:
        """
        Получить список курсов.
        
        Args:
            db: Сессия БД
            only_published: Только опубликованные курсы
        
        Returns:
            Список курсов
        """
        query = select(Course)
        
        if only_published:
            query = query.where(Course.is_published)
        
        query = query.order_by(Course.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_course_by_id(
        db: AsyncSession,
        course_id: UUID,
        include_modules: bool = False,
        only_published: bool = False,
    ) -> Course | None:
        """
        Получить курс по ID.

        Args:
            db: Сессия БД
            course_id: UUID курса
            include_modules: Загрузить модули курса
            only_published: Только опубликованный курс (для публичного API)

        Returns:
            Course или None
        """
        query = select(Course).where(Course.id == course_id)
        if only_published:
            query = query.where(Course.is_published.is_(True))

        if include_modules:
            query = query.options(
                selectinload(Course.modules).selectinload(Module.lessons)
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_course_stats(db: AsyncSession, course_id: UUID) -> dict:
        """
        Получить статистику курса (количество модулей, уроков, общая длительность).
        
        Args:
            db: Сессия БД
            course_id: UUID курса
        
        Returns:
            Словарь со статистикой
        """
        # Количество модулей
        modules_count_query = select(func.count(Module.id)).where(
            Module.course_id == course_id,
            Module.is_published
        )
        modules_count_result = await db.execute(modules_count_query)
        modules_count = modules_count_result.scalar()
        
        # Количество уроков и общая длительность
        lessons_query = select(
            func.count(Lesson.id),
            func.sum(Lesson.duration_seconds)
        ).join(Module).where(
            Module.course_id == course_id,
            Module.is_published
        )
        lessons_result = await db.execute(lessons_query)
        lessons_count, total_duration = lessons_result.one()
        
        return {
            "modules_count": modules_count or 0,
            "lessons_count": lessons_count or 0,
            "total_duration": total_duration or 0
        }
