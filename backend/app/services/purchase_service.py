from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course
from app.models.purchase import Purchase
from app.models.user import User
from app.models.progress import Progress
from app.models.module import Module
from app.models.lesson import Lesson
from app.schemas.purchase import PurchaseCreate, TariffType


class PurchaseService:
    @staticmethod
    async def create_purchase(
        db: AsyncSession,
        user_id: UUID,
        data: PurchaseCreate
    ) -> Purchase:
        """
        Создать заказ на покупку курса.
        """
        # 1. Получаем курс
        query = select(Course).where(Course.id == data.course_id)
        result = await db.execute(query)
        course = result.scalars().first()
        
        if not course:
            raise ValueError("Course not found")
            
        # 2. Определяем цену и срок действия
        if data.tariff == TariffType.SELF:
            price_rub = course.price_self
            # Пример: доступ на 3 месяца
            expires_delta = timedelta(days=90) 
        else: # SUPPORT
            price_rub = course.price_support
            # Пример: доступ на 6 месяцев
            expires_delta = timedelta(days=180)
            
        amount_kopecks = price_rub * 100
        expires_at = datetime.utcnow() + expires_delta
        
        # 3. Создаем запись
        purchase = Purchase(
            user_id=user_id,
            course_id=data.course_id,
            tariff=data.tariff.value,
            amount_kopecks=amount_kopecks,
            payment_status="pending", # Сразу pending
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        
        db.add(purchase)
        await db.commit()
        await db.refresh(purchase)
        
        return purchase

    @staticmethod
    async def get_user_purchases(
        db: AsyncSession,
        user_id: UUID
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
        purchase_id: UUID
    ) -> Purchase | None:
        """Получить покупку по ID."""
        query = select(Purchase).where(Purchase.id == purchase_id)
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_my_courses_with_progress(
        db: AsyncSession,
        user_id: UUID
    ) -> list[dict]:
        """Получить курсы пользователя с прогрессом."""
        # 1. Получаем покупки (только успешные)
        purchases_query = (
            select(Purchase)
            .where(
                and_(
                    Purchase.user_id == user_id,
                    Purchase.payment_status == "success"
                )
            )
            .options(
                selectinload(Purchase.course)
                .selectinload(Course.modules)
                .selectinload(Module.lessons)
            )
            .order_by(Purchase.created_at.desc())
        )
        purchases_result = await db.execute(purchases_query)
        purchases = purchases_result.scalars().all()
        
        if not purchases:
            return []

        # 2. Получаем завершенные уроки
        progress_query = (
            select(Progress)
            .where(
                and_(
                    Progress.user_id == user_id,
                    Progress.is_completed == True
                )
            )
        )
        progress_result = await db.execute(progress_query)
        completed_lessons_ids = {p.lesson_id for p in progress_result.scalars().all()}
        
        response = []
        
        for purchase in purchases:
            course = purchase.course
            if not course:
                continue
                
            # Сортируем модули и уроки
            modules = sorted(course.modules, key=lambda m: m.order_index) if course.modules else []
            all_lessons = []
            
            for module in modules:
                if module.lessons:
                    module_lessons = sorted(module.lessons, key=lambda l: l.order_index)
                    all_lessons.extend(module_lessons)
            
            total_lessons = len(all_lessons)
            
            # Подсчет прогресса
            completed_in_course = 0
            for lesson in all_lessons:
                if lesson.id in completed_lessons_ids:
                    completed_in_course += 1
            
            progress_percent = int((completed_in_course / total_lessons * 100)) if total_lessons > 0 else 0
            
            # Поиск следующего урока
            last_lesson_id = None
            last_lesson_title = None
            
            # Ищем первый незавершенный урок
            for lesson in all_lessons:
                if lesson.id not in completed_lessons_ids:
                    last_lesson_id = lesson.id
                    last_lesson_title = lesson.title
                    break
            
            # Если все завершены или нет уроков, берем самый первый (или последний?)
            # Если курс пройден, можно предлагать последний или просто оставить как есть.
            # Если ничего не найдено (курс пройден), берем 1-й урок для повторения, или оставляем пустым
            if not last_lesson_id and total_lessons > 0:
                 # Если курс полностью пройден, можно отправить на 1 урок
                 last_lesson_id = all_lessons[0].id
                 last_lesson_title = all_lessons[0].title

            # Добавляем в результат
            response.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "progress": progress_percent,
                "total_lessons": total_lessons,
                "completed_lessons": completed_in_course,
                "last_lesson_id": last_lesson_id,
                "last_lesson_title": last_lesson_title,
                "cover_image_url": course.cover_image_url
            })
            
        return response
