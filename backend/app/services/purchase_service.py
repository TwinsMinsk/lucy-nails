from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.course import Course
from app.models.module import Module
from app.models.progress import Progress
from app.models.purchase import Purchase


class PurchaseService:
    @staticmethod
    async def get_active_purchase(
        db: AsyncSession,
        user_id: UUID,
        course_id: UUID,
    ) -> Purchase | None:
        """Активная успешная покупка (доступ не истёк)."""
        now = datetime.utcnow()
        result = await db.execute(
            select(Purchase).where(
                and_(
                    Purchase.user_id == user_id,
                    Purchase.course_id == course_id,
                    Purchase.payment_status == "success",
                    Purchase.expires_at > now,
                )
            )
            .order_by(Purchase.expires_at.desc(), Purchase.created_at.desc())
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_purchases(
        db: AsyncSession,
        user_id: UUID,
    ) -> list[Purchase]:
        """Получить все покупки пользователя."""
        query = (
            select(Purchase)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.created_at.desc())
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_purchase_by_id(
        db: AsyncSession,
        purchase_id: UUID,
    ) -> Purchase | None:
        """Получить покупку по ID."""
        query = select(Purchase).where(Purchase.id == purchase_id)
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_my_courses_with_progress(
        db: AsyncSession,
        user_id: UUID,
    ) -> list[dict]:
        """Только активные успешные покупки (expires_at > now)."""
        now = datetime.utcnow()
        purchases_query = (
            select(Purchase)
            .where(
                and_(
                    Purchase.user_id == user_id,
                    Purchase.payment_status == "success",
                    Purchase.expires_at > now,
                )
            )
            .options(
                selectinload(Purchase.course).selectinload(Course.modules).selectinload(Module.lessons),
            )
            .order_by(Purchase.created_at.desc())
        )
        purchases_result = await db.execute(purchases_query)
        purchases = purchases_result.scalars().all()

        if not purchases:
            return []

        progress_query = select(Progress).where(
            and_(
                Progress.user_id == user_id,
                Progress.is_completed,
            )
        )
        progress_result = await db.execute(progress_query)
        completed_lessons_ids = {p.lesson_id for p in progress_result.scalars().all()}

        support_invite = (settings.TELEGRAM_SUPPORT_GROUP_INVITE or "").strip() or None

        response = []
        for purchase in purchases:
            course = purchase.course
            if not course:
                continue

            modules = (
                sorted(
                    [module for module in course.modules if module.is_published],
                    key=lambda m: m.order_index,
                )
                if course.modules
                else []
            )
            all_lessons = []
            for module in modules:
                if module.lessons:
                    module_lessons = sorted(module.lessons, key=lambda l: l.order_index)
                    all_lessons.extend(module_lessons)

            total_lessons = len(all_lessons)

            completed_in_course = 0
            for lesson in all_lessons:
                if lesson.id in completed_lessons_ids:
                    completed_in_course += 1

            progress_percent = int((completed_in_course / total_lessons * 100)) if total_lessons > 0 else 0

            last_lesson_id = None
            last_lesson_title = None
            for lesson in all_lessons:
                if lesson.id not in completed_lessons_ids:
                    last_lesson_id = lesson.id
                    last_lesson_title = lesson.title
                    break

            if not last_lesson_id and total_lessons > 0:
                last_lesson_id = all_lessons[0].id
                last_lesson_title = all_lessons[0].title

            support_chat_url = None
            if purchase.tariff == "support" and support_invite:
                support_chat_url = support_invite

            response.append(
                {
                    "id": course.id,
                    "title": course.title,
                    "description": course.description,
                    "progress": progress_percent,
                    "total_lessons": total_lessons,
                    "completed_lessons": completed_in_course,
                    "last_lesson_id": last_lesson_id,
                    "last_lesson_title": last_lesson_title,
                    "cover_image_url": course.cover_image_url,
                    "tariff": purchase.tariff,
                    "expires_at": purchase.expires_at,
                    "support_chat_url": support_chat_url,
                }
            )

        return response
