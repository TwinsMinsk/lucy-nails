from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lesson import Lesson
from app.models.module import Module
from app.models.progress import Progress
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.progress import ProgressUpdate


class LessonService:
    @staticmethod
    async def get_lesson_by_id(
        db: AsyncSession, 
        lesson_id: UUID
    ) -> Lesson | None:
        """
        Получить урок по ID с загрузкой модуля и курса.
        """
        query = (
            select(Lesson)
            .options(
                selectinload(Lesson.module).selectinload(Module.course)
            )
            .where(Lesson.id == lesson_id)
        )
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def check_access(
        db: AsyncSession,
        user: User,
        lesson: Lesson
    ) -> bool:
        """
        Проверить доступ пользователя к уроку.
        Доступ есть если:
        1. Урок - превью (is_preview=True)
        2. Пользователь - админ
        3. Есть активная покупка курса
        """
        if lesson.is_preview:
            return True
            
        if user.role == "admin":
            return True
            
        # Проверка покупки
        course_id = lesson.module.course_id
        now = datetime.utcnow()
        
        query = select(Purchase).where(
            and_(
                Purchase.user_id == user.id,
                Purchase.course_id == course_id,
                Purchase.payment_status == "success",  # Используем 'success' согласно ENUM
                Purchase.expires_at > now
            )
        ).order_by(Purchase.expires_at.desc(), Purchase.created_at.desc())
        result = await db.execute(query)
        purchase = result.scalars().first()
        
        return purchase is not None

    @staticmethod
    async def get_lesson_with_access(
        db: AsyncSession,
        lesson_id: UUID,
        user: User
    ) -> tuple[Lesson | None, bool]:
        """
        Получить урок и флаг доступа к видео.
        
        Returns:
            (Lesson, has_access)
        """
        lesson = await LessonService.get_lesson_by_id(db, lesson_id)
        if not lesson:
            return None, False

        mod = lesson.module
        if not mod or not mod.course:
            return None, False

        # Для не-админов не отдаём уроки неопубликованного курса/модуля
        if user.role != "admin":
            if not mod.is_published or not mod.course.is_published:
                return None, False

        has_access = await LessonService.check_access(db, user, lesson)
        return lesson, has_access

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        user_id: UUID,
        lesson_id: UUID,
        data: ProgressUpdate
    ) -> Progress:
        """
        Обновить или создать запись о прогрессе.
        """
        lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = lesson_result.scalars().first()
        max_watched_seconds = lesson.duration_seconds if lesson else data.watched_seconds
        watched_seconds = max(0, min(data.watched_seconds, max_watched_seconds))

        # Проверяем существование записи
        query = select(Progress).where(
            and_(
                Progress.user_id == user_id,
                Progress.lesson_id == lesson_id
            )
        )
        result = await db.execute(query)
        progress = result.scalars().first()
        
        if progress:
            # Обновляем
            progress.watched_seconds = watched_seconds
            
            # Если статус поменялся на completed
            if data.is_completed and not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = datetime.utcnow()
            elif not data.is_completed:
                 # Если вдруг сбросили (редкий кейс, но пусть будет)
                 progress.is_completed = False
                 progress.completed_at = None
                 
            # Если уже completed, не меняем completed_at
        else:
            # Создаем новую
            progress = Progress(
                user_id=user_id,
                lesson_id=lesson_id,
                watched_seconds=watched_seconds,
                is_completed=data.is_completed,
                completed_at=datetime.utcnow() if data.is_completed else None
            )
            db.add(progress)
            
        await db.commit()
        await db.refresh(progress)
        return progress

    @staticmethod
    async def get_progress(
        db: AsyncSession,
        user_id: UUID,
        lesson_id: UUID
    ) -> Progress | None:
        """Получить текущий прогресс."""
        query = select(Progress).where(
            and_(
                Progress.user_id == user_id,
                Progress.lesson_id == lesson_id
            )
        )
        result = await db.execute(query)
        return result.scalars().first()
