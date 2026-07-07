"""
Сервис для вычисления прогресса пользователя по курсу.
"""

from typing import NamedTuple
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.models.module import Module
from app.models.progress import Progress


class CourseCompletion(NamedTuple):
    """Результат подсчета прогресса пользователя по курсу."""

    total_lessons: int
    completed_lesson_ids: list[UUID]

    @property
    def completed_count(self) -> int:
        return len(self.completed_lesson_ids)

    @property
    def is_complete(self) -> bool:
        return self.total_lessons > 0 and len(self.completed_lesson_ids) == self.total_lessons

    @property
    def percent(self) -> int:
        if self.total_lessons == 0:
            return 0
        return int((self.completed_count / self.total_lessons) * 100)


class ProgressService:
    """Сервис для вычисления прогресса пользователя по курсу."""

    @staticmethod
    async def get_course_completion(db: AsyncSession, user_id: UUID, course_id: UUID) -> CourseCompletion:
        """
        Посчитать прогресс пользователя по курсу.

        Args:
            db: Сессия БД
            user_id: UUID пользователя
            course_id: UUID курса

        Returns:
            CourseCompletion с общим количеством уроков и списком завершенных
        """
        # 1. Получаем все уроки курса для подсчета общего количества
        # Используем join для эффективности
        query_lessons = (
            select(Lesson.id)
            .join(Module, Module.id == Lesson.module_id)
            .where(
                and_(
                    Module.course_id == course_id,
                    Module.is_published.is_(True),
                )
            )
        )
        result_lessons = await db.execute(query_lessons)
        all_lesson_ids = result_lessons.scalars().all()
        total_lessons = len(all_lesson_ids)

        if total_lessons == 0:
            return CourseCompletion(total_lessons=0, completed_lesson_ids=[])

        # 2. Получаем завершенные уроки пользователя для этого курса
        query_progress = (
            select(Progress.lesson_id)
            .where(
                and_(
                    Progress.user_id == user_id,
                    Progress.is_completed,
                    Progress.lesson_id.in_(all_lesson_ids)
                )
            )
        )
        result_progress = await db.execute(query_progress)
        completed_lesson_ids = result_progress.scalars().all()

        return CourseCompletion(
            total_lessons=total_lessons,
            completed_lesson_ids=list(completed_lesson_ids),
        )
