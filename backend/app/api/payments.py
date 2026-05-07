"""
Payments API: webhook Prodamus + генерация платёжной ссылки.
"""

import logging
import secrets
from datetime import datetime, timedelta
from email.utils import parseaddr
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
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


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    allowed = {"+", "-", " ", "(", ")"}
    if any(not (char.isdigit() or char in allowed) for char in s) or len(s) > 32:
        raise HTTPException(status_code=422, detail="Invalid customer_phone")
    return s or None


_email_adapter = TypeAdapter(EmailStr)


def _normalize_email(raw: Any) -> str:
    if not raw:
        logger.error("Prodamus webhook: no customer_email in payload")
        raise HTTPException(status_code=422, detail="customer_email is required")

    candidate = str(raw).strip().lower()
    try:
        return str(_email_adapter.validate_python(candidate))
    except ValidationError:
        logger.error("Prodamus webhook: invalid customer_email=%s", parseaddr(candidate)[1])
        raise HTTPException(status_code=422, detail="Invalid customer_email")


def parse_checkout_order_id(order_id_raw: str) -> tuple[UUID, str] | None:
    """
    Формат: course|<course_uuid>|self|support|<nonce_hex>
    Разделитель — | (uuid содержит дефисы, но не |).
    """
    if not order_id_raw or "|" not in order_id_raw:
        return None
    parts = order_id_raw.split("|")
    if len(parts) != 4 or parts[0] != "course":
        return None
    try:
        course_id = UUID(parts[1])
    except ValueError:
        return None
    tariff = parts[2]
    if tariff not in ("self", "support"):
        return None
    return course_id, tariff


async def _get_or_create_user(
    db: AsyncSession,
    email: str,
    phone: str | None,
) -> tuple[User, str | None]:
    """
    Находит пользователя по email или создаёт нового с случайным паролем (payment-first).

    Returns:
        (user, plain_password) — plain_password только для нового пользователя (для email).
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user:
        return user, None

    plain = secrets.token_urlsafe(10)
    user = User(
        email=email,
        password_hash=get_password_hash(plain),
        phone=phone,
        role="student",
    )
    db.add(user)
    await db.flush()
    return user, plain


def _build_prodamus_order_id(course_id: UUID, tariff: str) -> str:
    nonce = secrets.token_hex(8)
    return f"course|{course_id}|{tariff}|{nonce}"


def _resolve_payment_key(order_num_raw: Any, order_id_raw: str) -> str:
    """Returns a stable idempotency key for Prodamus webhook processing."""
    if order_num_raw is not None and str(order_num_raw).strip() != "":
        return str(order_num_raw).strip()
    return f"order_id:{order_id_raw}"


def _is_success_payment_payload(payload: dict[str, Any]) -> bool:
    """Accepts common Prodamus success markers and ignores empty status fields."""
    status_markers = [
        payload.get("payment_status"),
        payload.get("status"),
        payload.get("result"),
    ]
    normalized = {str(value).strip().lower() for value in status_markers if value not in (None, "")}
    if not normalized:
        return True
    success_values = {"success", "paid", "ok", "completed", "succeeded", "1", "true"}
    return any(value in success_values for value in normalized)


async def _resolve_course_for_checkout(
    db: AsyncSession,
    course_id_str: str,
) -> Course:
    if course_id_str == "default":
        result = await db.execute(select(Course).where(Course.is_published.is_(True)).limit(1))
    else:
        try:
            cid = UUID(course_id_str)
        except ValueError:
            raise HTTPException(status_code=404, detail="Course not found")
        result = await db.execute(select(Course).where(Course.id == cid))
    course = result.scalars().first()
    if not course or not course.is_published:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _checkout_link_for_course(
    course: Course,
    tariff: str,
    *,
    customer_email: str | None = None,
    customer_phone: str | None = None,
) -> str:
    if tariff not in ("self", "support"):
        raise HTTPException(status_code=400, detail="Invalid tariff")
    price = float(course.price_self if tariff == "self" else course.price_support)
    course_name = f"{course.title} — {'Самостоятельный' if tariff == 'self' else 'С поддержкой'}"
    order_id = _build_prodamus_order_id(course.id, tariff)
    return ProdamusService.generate_payment_link(
        course_name=course_name,
        price=price,
        tariff=tariff,
        order_id=order_id,
        customer_email=customer_email,
        customer_phone=customer_phone,
    )


# ---------------------------------------------------------------------------
# Endpoint: POST /api/payments/webhook
# ---------------------------------------------------------------------------


@router.post(
    "/webhook",
    summary="Webhook от Prodamus (оповещение об успешной оплате)",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("120/minute")
async def prodamus_webhook(request: Request) -> dict[str, str]:
    """
    Принимает вебхук Prodamus после успешной оплаты.

    Единственное подтверждение оплаты — валидная подпись и этот webhook
    (редирект urlSuccess не гарантирует оплату).
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    signature = request.headers.get("Sign", "")
    if not signature:
        logger.warning("Prodamus webhook: no Sign header")
        raise HTTPException(status_code=400, detail="Missing signature")

    if not ProdamusService.verify_signature(payload, signature):
        logger.warning("Prodamus webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if not _is_success_payment_payload(payload):
        logger.warning("Prodamus webhook: non-success payment payload")
        raise HTTPException(status_code=422, detail="Payment is not successful")

    order_id_raw = str(payload.get("order_id", "")).strip()
    parsed = parse_checkout_order_id(order_id_raw)
    if not parsed:
        logger.error("Prodamus webhook: invalid order_id=%s", order_id_raw)
        raise HTTPException(status_code=422, detail="Invalid order_id")

    course_id_uuid, tariff = parsed
    payment_key = _resolve_payment_key(payload.get("order_num"), order_id_raw)
    customer_email = ""
    plain_password_for_email: str | None = None

    try:
        async with async_session_maker() as db:
            existing_pay = await db.execute(select(Purchase).where(Purchase.payment_id == payment_key))
            if existing_pay.scalars().first():
                return {"status": "ok"}

            customer_email = _normalize_email(payload.get("customer_email"))

            customer_phone = _normalize_phone(payload.get("customer_phone"))

            course_result = await db.execute(select(Course).where(Course.id == course_id_uuid))
            course = course_result.scalars().first()
            if not course or not course.is_published:
                logger.error("Prodamus webhook: course not found or unpublished %s", course_id_uuid)
                raise HTTPException(status_code=422, detail="Course not found")

            amount_str: str = str(payload.get("sum", "0")).replace(",", ".")
            try:
                paid_kopecks = int(round(float(amount_str) * 100))
            except ValueError:
                paid_kopecks = 0

            expected_rub = course.price_self if tariff == "self" else course.price_support
            expected_kopecks = int(expected_rub) * 100
            if abs(paid_kopecks - expected_kopecks) > 2:
                logger.error(
                    "Prodamus webhook: amount mismatch expected_kop=%s got_kop=%s",
                    expected_kopecks,
                    paid_kopecks,
                )
                raise HTTPException(status_code=422, detail="Amount mismatch")

            currency = str(payload.get("currency", "rub")).lower()
            if currency not in ("rub", "rur"):
                logger.error("Prodamus webhook: unsupported currency=%s", currency)
                raise HTTPException(status_code=422, detail="Unsupported currency")

            user, plain_password = await _get_or_create_user(db, customer_email, customer_phone)

            if customer_phone and not user.phone:
                user.phone = customer_phone

            paid_at = datetime.utcnow()
            expires_at = paid_at + timedelta(days=settings.COURSE_ACCESS_DAYS)

            purchase = Purchase(
                user_id=user.id,
                course_id=course.id,
                tariff=tariff,
                amount_kopecks=paid_kopecks,
                payment_id=payment_key,
                payment_status="success",
                paid_at=paid_at,
                customer_phone=customer_phone,
                expires_at=expires_at,
            )
            db.add(purchase)

            await db.commit()
            plain_password_for_email = plain_password

    except IntegrityError:
        logger.info("Prodamus webhook duplicate payment_key=%s", payment_key)
        return {"status": "ok"}

    if plain_password_for_email:
        try:
            await EmailService.send_credentials(customer_email, plain_password_for_email)
        except Exception:
            logger.exception("Failed to send credentials email to %s", customer_email)

    logger.info(
        "Webhook processed: user=%s course=%s tariff=%s",
        customer_email,
        course_id_uuid,
        tariff,
    )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoint: POST /api/payments/link
# ---------------------------------------------------------------------------


class PaymentLinkRequest(BaseModel):
    course_id: str
    tariff: str  # "self" | "support"
    customer_email: str | None = None
    customer_phone: str | None = None


class GuestPaymentLinkRequest(BaseModel):
    course_id: str
    tariff: Literal["self", "support"]
    customer_email: EmailStr
    customer_phone: str | None = None


@router.post(
    "/guest-link",
    summary="Ссылка на оплату Prodamus без регистрации (email/телефон в форме)",
)
@limiter.limit("20/minute")
async def get_guest_payment_link(
    request: Request,
    data: GuestPaymentLinkRequest,
) -> dict[str, str]:
    """Гостевая оплата: после webhook создаётся аккаунт и отправляется пароль на email."""
    async with async_session_maker() as db:
        course = await _resolve_course_for_checkout(db, data.course_id)

    email_normalized = str(data.customer_email).strip().lower()
    phone = _normalize_phone(data.customer_phone)
    link = _checkout_link_for_course(
        course,
        data.tariff,
        customer_email=email_normalized,
        customer_phone=phone,
    )
    return {"url": link}


@router.post(
    "/link",
    summary="Сгенерировать ссылку на оплату Prodamus",
)
@limiter.limit("60/minute")
async def get_payment_link(
    request: Request,
    data: PaymentLinkRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Возвращает ссылку на оплату для выбранного тарифа авторизованного пользователя."""
    async with async_session_maker() as db:
        course = await _resolve_course_for_checkout(db, data.course_id)

    link = _checkout_link_for_course(
        course,
        data.tariff,
        customer_email=current_user.email,
        customer_phone=_normalize_phone(data.customer_phone or current_user.phone),
    )
    return {"url": link}
