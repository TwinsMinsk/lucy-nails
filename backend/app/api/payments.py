"""
Payments API: webhook Prodamus + генерация платёжной ссылки.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.security import create_account_activation_token, get_password_hash
from app.models.course import Course
from app.models.order import Order
from app.models.purchase import Purchase
from app.models.payment_event import PaymentEvent
from app.models.user import User
from app.services.outbox_service import enqueue_outbox_message
from app.services.runtime_settings_service import RuntimeSettingsService
from app.services.prodamus_service import ProdamusService
from app.services.access_service import AccessService
from app.services.payment_event_service import (
    PaymentEventData,
    build_payment_event_data,
    new_payment_event,
    record_terminal_payment_event,
)
from app.services.analytics_service import AnalyticsService
from app.services.analytics_service import contains_sensitive_analytics_value

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
        logger.error("Prodamus webhook: invalid customer email")
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


def _parse_persisted_order_id(order_id_raw: str) -> UUID | None:
    parts = order_id_raw.split("|")
    if len(parts) != 2 or parts[0] != "order":
        return None
    try:
        return UUID(parts[1])
    except ValueError:
        return None


def _hash_status_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _ensure_checkout_enabled(db: AsyncSession) -> None:
    if not await RuntimeSettingsService.checkout_enabled(
        db, default_enabled=settings.CHECKOUT_ENABLED
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkout is temporarily unavailable",
        )


async def _get_or_create_user(
    db: AsyncSession,
    email: str,
    phone: str | None,
) -> tuple[User, bool]:
    """
    Находит пользователя по email или создаёт нового с случайным паролем (payment-first).

    Returns:
        (user, plain_password) — plain_password только для нового пользователя (для email).
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user:
        return user, False

    unusable_secret = secrets.token_urlsafe(48)
    user = User(
        email=email,
        password_hash=get_password_hash(unusable_secret),
        phone=phone,
        role="student",
    )
    db.add(user)
    await db.flush()
    return user, True


def _build_prodamus_order_id(course_id: UUID, tariff: str) -> str:
    nonce = secrets.token_hex(8)
    return f"course|{course_id}|{tariff}|{nonce}"


async def _create_checkout_order(
    db: AsyncSession,
    course: Course,
    tariff: str,
    customer_email: str,
    customer_phone: str | None,
    *,
    user_id: UUID | None = None,
    attribution: dict[str, Any] | None = None,
) -> tuple[Order, str]:
    if tariff not in ("self", "support"):
        raise HTTPException(status_code=400, detail="Invalid tariff")
    status_token = secrets.token_urlsafe(32)
    price_rub = course.price_self if tariff == "self" else course.price_support
    attribution = attribution or {}
    first_touch = attribution.get("first_touch") or {}
    last_touch = attribution.get("last_touch") or {}
    order = Order(
        user_id=user_id,
        course_id=course.id,
        course_title=course.title,
        tariff=tariff,
        customer_email=customer_email,
        customer_phone=customer_phone,
        amount_kopecks=int(price_rub) * 100,
        currency="RUB",
        access_days=course.access_days,
        status="pending",
        status_token_hash=_hash_status_token(status_token),
        first_utm_source=first_touch.get("utm_source"),
        first_utm_medium=first_touch.get("utm_medium"),
        first_utm_campaign=first_touch.get("utm_campaign"),
        first_utm_content=first_touch.get("utm_content"),
        first_utm_term=first_touch.get("utm_term"),
        last_utm_source=last_touch.get("utm_source"),
        last_utm_medium=last_touch.get("utm_medium"),
        last_utm_campaign=last_touch.get("utm_campaign"),
        last_utm_content=last_touch.get("utm_content"),
        last_utm_term=last_touch.get("utm_term"),
    )
    db.add(order)
    await db.flush()
    event_values = {
        "anonymous_id": attribution.get("anonymous_id"),
        "user_id": user_id,
        "order_id": order.id,
        "course_id": course.id,
        "utm_source": first_touch.get("utm_source"),
        "utm_medium": first_touch.get("utm_medium"),
        "utm_campaign": first_touch.get("utm_campaign"),
        "utm_content": first_touch.get("utm_content"),
        "utm_term": first_touch.get("utm_term"),
        "properties": {"tariff": tariff},
    }
    await AnalyticsService.record_event(
        db,
        event_id=f"checkout_started:{order.id}",
        event_name="checkout_started",
        source="server",
        **event_values,
    )
    await AnalyticsService.record_event(
        db,
        event_id=f"payment_redirect:{order.id}",
        event_name="payment_redirect",
        source="server",
        **event_values,
    )
    return order, status_token


def _resolve_payment_key(provider_order_id_raw: Any, merchant_reference_raw: Any) -> str:
    """Return the provider payment id, retaining legacy callback compatibility."""
    provider_order_id = str(provider_order_id_raw or "").strip()
    merchant_reference = str(merchant_reference_raw or "").strip()
    provider_contains_legacy_reference = bool(
        _parse_persisted_order_id(provider_order_id)
        or parse_checkout_order_id(provider_order_id)
    )
    if provider_order_id and not provider_contains_legacy_reference:
        return provider_order_id
    # Older application fixtures and callbacks inverted the two fields. Keep
    # accepting them during rollout, but never prefer a merchant reference to
    # a genuine Prodamus order_id.
    if merchant_reference and provider_contains_legacy_reference:
        return merchant_reference
    return f"order_id:{provider_order_id}"


def _is_success_payment_payload(payload: dict[str, Any]) -> bool:
    """Require an explicit success marker; an empty/absent status is NOT success."""
    status_markers = [
        payload.get("payment_status"),
        payload.get("status"),
        payload.get("result"),
    ]
    normalized = {str(value).strip().lower() for value in status_markers if value not in (None, "")}
    if not normalized:
        return False
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
    order_id: str | None = None,
    status_token: str | None = None,
) -> str:
    if tariff not in ("self", "support"):
        raise HTTPException(status_code=400, detail="Invalid tariff")
    price = float(course.price_self if tariff == "self" else course.price_support)
    course_name = f"{course.title} — {'Самостоятельный' if tariff == 'self' else 'С поддержкой'}"
    order_id = order_id or _build_prodamus_order_id(course.id, tariff)
    success_url = None
    if status_token:
        success_query = urlencode({"order_id": order_id, "token": status_token})
        success_url = f"{settings.FRONTEND_URL.rstrip('/')}/payment-success?{success_query}"
    return ProdamusService.generate_payment_link(
        course_name=course_name,
        price=price,
        tariff=tariff,
        order_id=order_id,
        customer_email=customer_email,
        customer_phone=customer_phone,
        success_url=success_url,
    )


# ---------------------------------------------------------------------------
# Endpoint: POST /api/payments/webhook
# ---------------------------------------------------------------------------


async def _record_purchase_once(
    payment_key: str,
    course_id_uuid: UUID | None,
    tariff: str | None,
    payload: dict[str, Any],
    event_data: PaymentEventData,
    order_uuid: UUID | None = None,
) -> str:
    """One attempt at recording the purchase in its own transaction.

    The purchase and its notification are committed atomically. External
    delivery is handled later by the outbox worker.
    """
    webhook_email = _normalize_email(payload.get("customer_email"))
    async with async_session_maker() as db:
        existing_event = await db.scalar(
            select(PaymentEvent.id).where(PaymentEvent.event_hash == event_data.event_hash)
        )
        if existing_event is not None:
            return webhook_email

        payment_event = new_payment_event(event_data, order_id=order_uuid)
        db.add(payment_event)
        await db.flush()

        existing_pay = await db.execute(select(Purchase).where(Purchase.payment_id == payment_key))
        existing_purchase = existing_pay.scalars().first()
        if existing_purchase:
            payment_event.purchase_id = existing_purchase.id
            payment_event.processing_status = "duplicate"
            payment_event.processed_at = datetime.utcnow()
            await db.commit()
            return webhook_email

        order: Order | None = None
        if order_uuid is not None:
            order_result = await db.execute(
                select(Order).where(Order.id == order_uuid).with_for_update()
            )
            order = order_result.scalar_one_or_none()
            if order is None:
                raise HTTPException(status_code=422, detail="Order not found")
            if webhook_email != order.customer_email:
                raise HTTPException(status_code=422, detail="Order customer mismatch")
            course_id_uuid = order.course_id
            tariff = order.tariff

        if course_id_uuid is None or tariff is None:
            raise HTTPException(status_code=422, detail="Invalid order_id")

        customer_email = order.customer_email if order else webhook_email

        customer_phone = _normalize_phone(payload.get("customer_phone"))

        course_result = await db.execute(select(Course).where(Course.id == course_id_uuid))
        course = course_result.scalars().first()
        if not course or (order is None and not course.is_published):
            logger.error("Prodamus webhook: course unavailable %s", course_id_uuid)
            raise HTTPException(status_code=422, detail="Course not found")

        amount_str: str = str(payload.get("sum", "0")).replace(",", ".")
        try:
            paid_kopecks = int(round(float(amount_str) * 100))
        except ValueError:
            paid_kopecks = 0

        expected_kopecks = (
            order.amount_kopecks
            if order is not None
            else int(course.price_self if tariff == "self" else course.price_support) * 100
        )
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

        user, is_new_user = await _get_or_create_user(db, customer_email, customer_phone)

        if customer_phone and not user.phone:
            user.phone = customer_phone

        paid_at = datetime.utcnow()
        access_days = order.access_days if order is not None else settings.COURSE_ACCESS_DAYS
        expires_at = paid_at + timedelta(days=access_days)

        purchase = Purchase(
            user_id=user.id,
            course_id=course.id,
            order_id=order.id if order else None,
            tariff=tariff,
            amount_kopecks=paid_kopecks,
            payment_id=payment_key,
            payment_status="success",
            paid_at=paid_at,
            customer_phone=customer_phone,
            expires_at=expires_at,
        )
        db.add(purchase)
        await db.flush()
        payment_event.purchase_id = purchase.id
        entitlement = AccessService.create_purchase_entitlement(purchase)
        db.add(entitlement)
        await db.flush()
        await AccessService.enqueue_support_group_restore(db, entitlement)
        dedupe_hash = hashlib.sha256(payment_key.encode("utf-8")).hexdigest()
        if is_new_user:
            activation_token = create_account_activation_token(user.id, user.token_version)
            activation_url = (
                f"{settings.FRONTEND_URL.rstrip('/')}/auth/activate?token={activation_token}"
            )
            enqueue_outbox_message(
                db,
                kind="account_activation",
                recipient=customer_email,
                payload={
                    "activation_url": activation_url,
                    "course_title": course.title,
                    "expires_at": expires_at.isoformat(),
                },
                dedupe_key=f"payment:{dedupe_hash}:activation",
            )
        else:
            enqueue_outbox_message(
                db,
                kind="access_granted",
                recipient=customer_email,
                payload={
                    "login_url": f"{settings.FRONTEND_URL.rstrip('/')}/auth/login",
                    "course_title": course.title,
                    "expires_at": expires_at.isoformat(),
                },
                dedupe_key=f"payment:{dedupe_hash}:access",
            )
        if user.telegram_id is not None and settings.TELEGRAM_BOT_TOKEN:
            support_note = ""
            if tariff == "support" and settings.TELEGRAM_SUPPORT_GROUP_INVITE:
                support_note = (
                    f"\nЧат поддержки: {settings.TELEGRAM_SUPPORT_GROUP_INVITE}"
                )
            enqueue_outbox_message(
                db,
                kind="access_granted",
                channel="telegram",
                recipient=str(user.telegram_id),
                payload={
                    "text": (
                        f"✅ Оплата подтверждена. Доступ к курсу «{course.title}» открыт "
                        f"до {expires_at:%d.%m.%Y}.{support_note}"
                    )
                },
                dedupe_key=f"payment:{dedupe_hash}:access:telegram",
            )
        if order is not None:
            order.status = "paid"
            order.paid_at = paid_at
        await AnalyticsService.record_event(
            db,
            event_id=f"purchase_confirmed:{payment_key}",
            event_name="purchase_confirmed",
            source="server",
            anonymous_id=None,
            user_id=user.id,
            order_id=order.id if order else None,
            course_id=course.id,
            utm_source=order.first_utm_source if order else None,
            utm_medium=order.first_utm_medium if order else None,
            utm_campaign=order.first_utm_campaign if order else None,
            utm_content=order.first_utm_content if order else None,
            utm_term=order.first_utm_term if order else None,
            properties={"tariff": tariff},
        )
        payment_event.processing_status = "processed"
        payment_event.processed_at = datetime.utcnow()
        await db.commit()
        return customer_email


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

    event_data = build_payment_event_data(payload)
    if not _is_success_payment_payload(payload):
        await record_terminal_payment_event(
            event_data,
            processing_status="ignored",
            error_code="payment_not_successful",
            error_detail="Signed webhook did not contain a successful payment status",
        )
        logger.warning("Prodamus webhook: non-success payment payload")
        raise HTTPException(status_code=422, detail="Payment is not successful")

    provider_order_id_raw = str(payload.get("order_id", "")).strip()
    merchant_reference_raw = str(payload.get("order_num", "")).strip()
    order_reference_raw = merchant_reference_raw
    order_uuid = _parse_persisted_order_id(order_reference_raw)
    parsed = parse_checkout_order_id(order_reference_raw) if order_uuid is None else None

    # Compatibility for callbacks produced while the old field mapping was
    # deployed. New checkout callbacks are always resolved through order_num.
    if order_uuid is None and not parsed:
        order_reference_raw = provider_order_id_raw
        order_uuid = _parse_persisted_order_id(order_reference_raw)
        parsed = (
            parse_checkout_order_id(order_reference_raw)
            if order_uuid is None
            else None
        )
    if order_uuid is None and not parsed:
        await record_terminal_payment_event(
            event_data,
            processing_status="rejected",
            error_code="invalid_order_reference",
            error_detail="Order reference has an unsupported format",
        )
        logger.error("Prodamus webhook: invalid merchant order reference")
        raise HTTPException(status_code=422, detail="Invalid order reference")

    course_id_uuid, tariff = parsed if parsed else (None, None)
    payment_key = _resolve_payment_key(
        provider_order_id_raw,
        merchant_reference_raw,
    )
    try:
        _normalize_email(payload.get("customer_email"))
    except HTTPException as exc:
        await record_terminal_payment_event(
            event_data,
            processing_status="rejected",
            error_code="invalid_customer_email",
            error_detail=str(exc.detail),
            order_id=order_uuid,
        )
        raise

    # Record the purchase, retrying once. A concurrent first-time buyer can hit a
    # users.email unique collision (two payments, same brand-new email): the racing
    # request commits the user, and the retry then finds it and inserts only the
    # Purchase — so a distinct second payment is never silently dropped. A genuine
    # duplicate payment_id short-circuits at the existing-purchase check.
    for attempt in range(2):
        try:
            await _record_purchase_once(
                payment_key, course_id_uuid, tariff, payload, event_data, order_uuid
            )
            break
        except HTTPException as exc:
            error_code = str(exc.detail).lower().replace(" ", "_")[:64]
            await record_terminal_payment_event(
                event_data,
                processing_status="rejected",
                error_code=error_code,
                error_detail=str(exc.detail),
                order_id=order_uuid,
            )
            raise
        except IntegrityError:
            if attempt == 0:
                continue
            async with async_session_maker() as db:
                done = await db.execute(select(Purchase).where(Purchase.payment_id == payment_key))
                if done.scalars().first():
                    logger.info("Prodamus webhook duplicate payment_key=%s", payment_key)
                    return {"status": "ok"}
            logger.error("Prodamus webhook: unresolved integrity error payment_key=%s", payment_key)
            raise

    logger.info(
        "Webhook processed: course=%s tariff=%s order=%s",
        course_id_uuid,
        tariff,
        order_uuid,
    )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoint: POST /api/payments/link
# ---------------------------------------------------------------------------


class AttributionTouch(BaseModel):
    utm_source: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=255)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_content: str | None = Field(default=None, max_length=255)
    utm_term: str | None = Field(default=None, max_length=255)

    @field_validator("*", mode="after")
    @classmethod
    def reject_personal_attribution(cls, value: str | None) -> str | None:
        if contains_sensitive_analytics_value(value):
            raise ValueError("Attribution must not contain personal data")
        return value


class CheckoutAttribution(BaseModel):
    anonymous_id: str | None = Field(default=None, min_length=8, max_length=128)
    first_touch: AttributionTouch | None = None
    last_touch: AttributionTouch | None = None


class PaymentLinkRequest(BaseModel):
    course_id: str
    tariff: str  # "self" | "support"
    customer_email: str | None = None
    customer_phone: str | None = None
    attribution: CheckoutAttribution | None = None


class GuestPaymentLinkRequest(BaseModel):
    course_id: str
    tariff: Literal["self", "support"]
    customer_email: EmailStr
    customer_phone: str | None = None
    attribution: CheckoutAttribution | None = None


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
        await _ensure_checkout_enabled(db)
        course = await _resolve_course_for_checkout(db, data.course_id)
        email_normalized = str(data.customer_email).strip().lower()
        phone = _normalize_phone(data.customer_phone)
        order, status_token = await _create_checkout_order(
            db,
            course,
            data.tariff,
            email_normalized,
            phone,
            attribution=data.attribution.model_dump() if data.attribution else None,
        )
        await db.commit()

    link = _checkout_link_for_course(
        course,
        data.tariff,
        customer_email=email_normalized,
        customer_phone=phone,
        order_id=f"order|{order.id}",
        status_token=status_token,
    )
    return {"url": link, "order_id": f"order|{order.id}", "status_token": status_token}


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
        await _ensure_checkout_enabled(db)
        course = await _resolve_course_for_checkout(db, data.course_id)
        phone = _normalize_phone(data.customer_phone or current_user.phone)
        order, status_token = await _create_checkout_order(
            db,
            course,
            data.tariff,
            current_user.email,
            phone,
            user_id=current_user.id,
            attribution=data.attribution.model_dump() if data.attribution else None,
        )
        await db.commit()

    link = _checkout_link_for_course(
        course,
        data.tariff,
        customer_email=current_user.email,
        customer_phone=phone,
        order_id=f"order|{order.id}",
        status_token=status_token,
    )
    return {"url": link, "order_id": f"order|{order.id}", "status_token": status_token}


@router.get("/orders/{order_id}/status")
async def get_order_status(order_id: str, token: str) -> dict[str, str]:
    order_uuid = _parse_persisted_order_id(order_id)
    if order_uuid is None:
        raise HTTPException(status_code=404, detail="Order not found")
    async with async_session_maker() as db:
        result = await db.execute(select(Order).where(Order.id == order_uuid))
        order = result.scalar_one_or_none()
    supplied_hash = _hash_status_token(token)
    if order is None or not hmac.compare_digest(order.status_token_hash, supplied_hash):
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": order.status}
