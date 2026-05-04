"""
Payments API: webhook Prodamus + генерация платёжной ссылки.
"""

import logging
import secrets
import string
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.course import Course
from app.models.purchase import Purchase
from app.models.user import User
from app.services.email_service import EmailService
from app.services.prodamus_service import ProdamusService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_password(length: int = 10) -> str:
    """Генерирует случайный надёжный пароль."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    # Гарантируем хотя бы одну цифру и один спецсимвол
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
        *[secrets.choice(alphabet) for _ in range(length - 3)],
    ]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


async def _get_or_create_user(
    db: AsyncSession,
    email: str,
) -> tuple[User, str | None]:
    """
    Возвращает (user, plain_password).
    plain_password is None если пользователь уже существовал.
    """
    result = await db.execute(select(User).where(User.email == email))
    user   = result.scalars().first()

    if user:
        return user, None

    plain_password = _generate_password()
    user = User(
        email=email,
        password_hash=get_password_hash(plain_password),
        role="student",
    )
    db.add(user)
    await db.flush()  # получаем user.id до commit
    return user, plain_password


# ---------------------------------------------------------------------------
# Endpoint: POST /api/payments/webhook
# ---------------------------------------------------------------------------

@router.post(
    "/webhook",
    summary="Webhook от Prodamus (оповещение об успешной оплате)",
    status_code=status.HTTP_200_OK,
)
async def prodamus_webhook(request: Request) -> dict[str, str]:
    """
    Принимает вебхук Prodamus после успешной оплаты.

    Алгоритм:
      1. Проверить подпись (заголовок Sign).
      2. Извлечь customer_email.
      3. Найти / создать пользователя.
      4. Активировать покупку курса.
      5. Отправить письмо с кредами (только новым пользователям).
    """
    # 1. Читаем тело — Prodamus шлёт form-data или JSON
    content_type = request.headers.get("content-type", "")
    payload: dict[str, Any]

    if "application/json" in content_type:
        payload = await request.json()
    else:
        # application/x-www-form-urlencoded
        form = await request.form()
        payload = dict(form)

    signature = request.headers.get("Sign", "")

    if not signature:
        logger.warning("Prodamus webhook: no Sign header")
        raise HTTPException(status_code=400, detail="Missing signature")

    # 2. Проверяем подпись
    if not ProdamusService.verify_signature(payload, signature):
        logger.warning("Prodamus webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 3. Извлекаем email покупателя
    customer_email: str | None = payload.get("customer_email")
    if not customer_email:
        logger.error("Prodamus webhook: no customer_email in payload")
        raise HTTPException(status_code=422, detail="customer_email is required")

    customer_email = customer_email.strip().lower()

    # 4. Извлекаем идентификатор заказа/курса из order_id
    #    Формат order_id: "course_<uuid>_<tariff>" (см. ProdamusService.generate_payment_link)
    order_id: str = payload.get("order_id", "")
    course_id_str: str | None  = None
    tariff: str = "self"

    if order_id.startswith("course_"):
        parts = order_id.split("_")
        if len(parts) >= 3:
            course_id_str = parts[1]
            tariff = parts[2]

    async with async_session_maker() as db:
        async with db.begin():
            # 5. Находим / создаём пользователя
            user, plain_password = await _get_or_create_user(db, customer_email)

            # 6. Находим курс (если передан order_id с course_id)
            course: Course | None = None
            if course_id_str:
                result = await db.execute(
                    select(Course).where(Course.id == course_id_str)
                )
                course = result.scalars().first()

            # Если курс не найден — берём первый опубликованный (fallback)
            if not course:
                result = await db.execute(
                    select(Course).where(Course.is_published).limit(1)
                )
                course = result.scalars().first()

            if not course:
                logger.error("Prodamus webhook: no course found for order_id=%s", order_id)
                raise HTTPException(status_code=422, detail="Course not found")

            # 7. Определяем сумму из вебхука
            amount_str: str = str(payload.get("sum", "0")).replace(",", ".")
            try:
                amount_kopecks = int(float(amount_str) * 100)
            except ValueError:
                amount_kopecks = 0

            # 8. Создаём или обновляем запись покупки
            existing_q = await db.execute(
                select(Purchase).where(
                    Purchase.user_id == user.id,
                    Purchase.course_id == course.id,
                )
            )
            purchase = existing_q.scalars().first()

            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(days=90 if tariff == "self" else 180)

            if purchase:
                purchase.payment_status = "success"
                purchase.tariff         = tariff
                purchase.amount_kopecks = amount_kopecks
                purchase.expires_at     = expires_at
            else:
                purchase = Purchase(
                    user_id=user.id,
                    course_id=course.id,
                    tariff=tariff,
                    amount_kopecks=amount_kopecks,
                    payment_status="success",
                    expires_at=expires_at,
                )
                db.add(purchase)

        # commit произошёл при выходе из db.begin()

        # 9. Отправляем email только новому пользователю
        if plain_password:
            try:
                await EmailService.send_credentials(
                    email=customer_email,
                    password=plain_password,
                )
            except Exception as exc:
                # Не роняем вебхук из-за ошибки email
                logger.error("Email send failed for %s: %s", customer_email, exc)

    logger.info(
        "Webhook processed: user=%s course=%s tariff=%s",
        customer_email,
        course.id if course else "?",
        tariff,
    )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoint: GET /api/payments/link
# ---------------------------------------------------------------------------

from pydantic import BaseModel


class PaymentLinkRequest(BaseModel):
    course_id: str
    tariff: str  # "self" | "support"


@router.post(
    "/link",
    summary="Сгенерировать ссылку на оплату Prodamus",
)
async def get_payment_link(data: PaymentLinkRequest) -> dict[str, str]:
    """
    Возвращает ссылку на оплату для выбранного тарифа.
    Используется кнопками на лендинге (или можно формировать на фронте через GET-params).
    """
    async with async_session_maker() as db:
        if data.course_id == "default":
            result = await db.execute(
                select(Course).where(Course.is_published).limit(1)
            )
        else:
            result = await db.execute(
                select(Course).where(Course.id == data.course_id)
            )
        course = result.scalars().first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    price = course.price_self if data.tariff == "self" else course.price_support
    course_name = f"{course.title} — {'Самостоятельный' if data.tariff == 'self' else 'С поддержкой'}"
    order_id = f"course_{course.id}_{data.tariff}"

    link = ProdamusService.generate_payment_link(
        course_name=course_name,
        price=float(price),
        tariff=data.tariff,
        order_id=order_id,
    )
    return {"url": link}
