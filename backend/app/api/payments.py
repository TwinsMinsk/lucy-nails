"""
Payments API: webhook Prodamus + генерация платёжной ссылки.
"""

import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Annotated, Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    TypeAdapter,
    ValidationError,
    ValidatorFunctionWrapHandler,
    WrapValidator,
    field_validator,
)
from sqlalchemy import Integer, func, literal, or_, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.dependencies import get_current_user
from app.core.legal import CONSENT_VERSION, require_consent
from app.core.rate_limit import limiter
from app.core.security import create_account_activation_token, get_password_hash
from app.models.analytics_event import AnalyticsEvent
from app.models.course import Course
from app.models.order import Order
from app.models.purchase import Purchase
from app.models.payment_event import PaymentEvent
from app.models.user import User
from app.services.outbox_service import (
    enqueue_outbox_message,
    enqueue_owner_telegram_alert,
    format_rub,
)
from app.services.runtime_settings_service import RuntimeSettingsService
from app.services.prodamus_service import ProdamusService, nest_form_fields, receipt_item_name
from app.services.access_service import AccessService
from app.services.email_service import format_msk_datetime
from app.services.payment_event_service import (
    PaymentEventData,
    build_payment_event_data,
    new_payment_event,
    parse_amount_kopecks,
    record_terminal_payment_event,
)
from app.services.analytics_service import AnalyticsService
from app.services.analytics_service import clean_attribution_value
from app.services.owner_alerts import enqueue_order_created_alert, payment_alert_email_lines
from app.services.support_links import issue_order_start_param

logger = logging.getLogger(__name__)

router = APIRouter()

# Only the self-paced tariff is sold. "support" is discontinued for new
# checkouts, but historical orders and webhooks may still reference it.
SELLABLE_TARIFFS = ("self",)
TARIFF_LABELS = {"self": "Самостоятельный", "support": "С поддержкой"}

# A Prodamus notification is a few kilobytes; the relay in front of the API
# caps bodies at the same size.
MAX_WEBHOOK_BODY_BYTES = 64 * 1024

# PostgreSQL aborts one side of a deadlock (40P01) or of a serialization
# conflict (40001); the aborted transaction can safely run again.
RETRYABLE_SQLSTATES = frozenset({"40P01", "40001"})

_SUCCESS_STATUS_VALUES = frozenset(
    {"success", "paid", "ok", "completed", "succeeded", "1", "true"}
)
# payment_status is the field of the Prodamus notification contract; status
# and result come from older callback shapes.
_AUTHORITATIVE_STATUS_FIELD = "payment_status"
_FALLBACK_STATUS_FIELDS = ("status", "result")

_ANALYTICS_EVENT_ID_LENGTH = AnalyticsEvent.__table__.c.event_id.type.length


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


def _webhook_email_or_none(raw: Any) -> str | None:
    """The buyer can edit the email on the Prodamus form; an order keeps its own."""
    try:
        return _normalize_email(raw)
    except HTTPException:
        return None


def _webhook_phone_or_none(raw: Any) -> str | None:
    # A payment must not be rejected because the form sent an unusual phone.
    try:
        return _normalize_phone(raw)
    except HTTPException:
        logger.warning("Prodamus webhook: unusual customer phone dropped")
        return None


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


# The success page polls for minutes; a buyer may come back to it the next day.
ORDER_STATUS_TOKEN_TTL = timedelta(hours=72)


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
    # Callers pass a lowercased email; func.lower() also matches legacy mixed-case rows.
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalars().first()
    if user:
        return user, False

    unusable_secret = secrets.token_urlsafe(48)
    user = User(
        email=email,
        password_hash=await run_in_threadpool(get_password_hash, unusable_secret),
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
    consented_at: datetime | None = None,
) -> tuple[Order, str]:
    if tariff not in SELLABLE_TARIFFS:
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
        offer_accepted_at=consented_at,
        personal_data_consent_at=consented_at,
        consent_version=CONSENT_VERSION if consented_at else None,
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
    await enqueue_order_created_alert(db, order)
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


def _status_marker(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()


def _payment_status_verdict(payload: dict[str, Any]) -> str:
    """Classify the status markers: "success", "not_successful" or "contradictory".

    An empty or absent status is NOT success. payment_status is authoritative
    whenever its key is present, even with a null or blank value: the other
    fields can never turn it into a success, only veto one. Only without the
    key do status and result decide. Markers that disagree about success never
    grant access: the notification is contradictory.
    """
    markers = [
        marker
        for field in _FALLBACK_STATUS_FIELDS
        if (marker := _status_marker(payload.get(field)))
    ]
    if _AUTHORITATIVE_STATUS_FIELD in payload:
        markers.append(_status_marker(payload[_AUTHORITATIVE_STATUS_FIELD]))
    successes = sum(marker in _SUCCESS_STATUS_VALUES for marker in markers)
    if successes == 0:
        return "not_successful"
    if successes < len(markers):
        return "contradictory"
    return "success"


def _purchase_confirmed_event_id(payment_key: str) -> str:
    """analytics_events.event_id is shorter than a provider payment id may be.

    A key that fits keeps the stored form ``purchase_confirmed:<key>``. A longer
    one is hashed under ``purchase_confirmed#sha256:``: no key can produce that
    form, because a literal key always follows a colon.
    """
    event_id = f"purchase_confirmed:{payment_key}"
    if len(event_id) <= _ANALYTICS_EVENT_ID_LENGTH:
        return event_id
    digest = hashlib.sha256(payment_key.encode("utf-8")).hexdigest()
    return f"purchase_confirmed#sha256:{digest}"


def _reference_identity(reference: str | None) -> tuple | None:
    """A merchant reference in comparable form, or None if it is not one.

    An order reference is identified by its order, a legacy checkout
    reference by its course, tariff and nonce: two checkouts of one course
    are two references.
    """
    reference = (reference or "").strip()
    order_uuid = _parse_persisted_order_id(reference)
    if order_uuid is not None:
        return ("order", order_uuid)
    if parse_checkout_order_id(reference) is not None:
        _, course_id, tariff, nonce = reference.split("|")
        return ("course", UUID(course_id), tariff, nonce)
    return None


def _named_reference(provider_order_id: str | None, merchant_reference: str | None) -> tuple | None:
    """The reference a notification names, resolved as the webhook resolves it:
    order_num first, then order_id for callbacks with the old field order."""
    return _reference_identity(merchant_reference) or _reference_identity(provider_order_id)


# Statuses of an event that bound a provider payment to its reference: it
# created the purchase, or it was a second payment for an already paid order.
_BINDING_EVENT_STATUSES = ("processed", "financial_incident")


@dataclass(frozen=True)
class PaymentBinding:
    """How a provider payment id is bound to a merchant reference.

    status: "unknown" (never accepted before), "same" (bound to the reference
    the notification names) or "other". purchase_id: the purchase the payment
    created, if any.
    """

    status: str
    purchase_id: UUID | None = None


def _proves_payment(purchase: Purchase) -> bool:
    # Historical manual grants were stored as purchases with admin_grant_ ids.
    return (
        purchase.transaction_kind == "paid"
        and purchase.payment_status == "success"
        and not (purchase.payment_id or "").startswith("admin_grant_")
    )


def _historical_purchase_matches(
    purchase: Purchase, reference: tuple, paid_kopecks: int | None
) -> bool:
    """Compare a purchase recorded without events with the notification."""
    if paid_kopecks is None or abs(paid_kopecks - purchase.amount_kopecks) > 2:
        return False
    if reference[0] == "order":
        return purchase.order_id == reference[1]
    _, course_id, tariff, _nonce = reference
    return (
        purchase.order_id is None
        and purchase.course_id == course_id
        and purchase.tariff == tariff
    )


async def _binding_events(db: AsyncSession, payment_key: str) -> list[PaymentEvent]:
    """Events that bound this provider payment id, under either field order."""
    lookups = {payment_key}
    if payment_key.startswith("order_id:"):
        lookups.add(payment_key.removeprefix("order_id:"))
    candidates = await db.scalars(
        select(PaymentEvent).where(
            PaymentEvent.processing_status.in_(_BINDING_EVENT_STATUSES),
            or_(
                PaymentEvent.external_event_id.in_(lookups),
                PaymentEvent.order_reference.in_(lookups),
            ),
        )
    )
    return [
        event
        for event in candidates
        if _resolve_payment_key(event.external_event_id, event.order_reference) == payment_key
    ]


async def _payment_binding(
    db: AsyncSession,
    payment_key: str,
    reference: tuple | None,
    paid_kopecks: int | None,
    known_purchase: Purchase | None,
) -> PaymentBinding:
    """Check a provider payment id against the reference a notification names.

    A provider payment this shop has accepted belongs to exactly one merchant
    reference. The proof is the event that processed its purchase, a recorded
    financial incident, or, for a historical purchase recorded before events,
    the purchase's own financial attributes. A manual grant proves no payment.
    """
    bound: set[tuple | None] = set()
    purchase_id: UUID | None = None
    if known_purchase is not None:
        if not _proves_payment(known_purchase):
            return PaymentBinding("other")
        purchase_id = known_purchase.id
        original = await db.scalar(
            select(PaymentEvent)
            .where(
                PaymentEvent.purchase_id == known_purchase.id,
                PaymentEvent.processing_status == "processed",
            )
            .order_by(PaymentEvent.received_at)
            .limit(1)
        )
        if original is not None:
            bound.add(_named_reference(original.external_event_id, original.order_reference))
        elif reference is not None and _historical_purchase_matches(
            known_purchase, reference, paid_kopecks
        ):
            bound.add(reference)
        else:
            return PaymentBinding("other", purchase_id)
    for event in await _binding_events(db, payment_key):
        bound.add(_named_reference(event.external_event_id, event.order_reference))
        if purchase_id is None and event.processing_status == "processed":
            purchase_id = event.purchase_id
    if not bound:
        return PaymentBinding("unknown")
    if reference is None or bound != {reference}:
        return PaymentBinding("other", purchase_id)
    return PaymentBinding("same", purchase_id)


def provider_payment_lock_keys(payment_key: str) -> tuple[int, int]:
    """Two signed int4 keys of the per-provider-payment advisory lock."""
    digest = hashlib.sha256(f"provider-payment:{payment_key}".encode("utf-8")).digest()
    return (
        int.from_bytes(digest[:4], byteorder="big", signed=True),
        int.from_bytes(digest[4:8], byteorder="big", signed=True),
    )


async def _lock_provider_payment(db: AsyncSession, payment_key: str) -> None:
    """Serialize deliveries of one provider payment id, whatever they name.

    Transaction-scoped; taken after the order lock, so the order stays the
    first lock a delivery takes.
    """
    key_high, key_low = provider_payment_lock_keys(payment_key)
    await db.execute(
        select(func.pg_advisory_xact_lock(literal(key_high, Integer), literal(key_low, Integer)))
    )


async def _supersede_duplicate_event(
    db: AsyncSession,
    stale: PaymentEvent,
    event_data: PaymentEventData,
    order_uuid: UUID | None,
) -> None:
    """Append a rejection next to a stored duplicate that does not hold.

    An older version could acknowledge a payment as a duplicate for a
    reference it does not belong to. That row is kept as it was; a rejected
    event that supersedes it is appended once, under a hash derived from it.
    """
    superseding_hash = hashlib.sha256(
        f"supersedes:{stale.event_hash}".encode("utf-8")
    ).hexdigest()
    if await db.scalar(
        select(PaymentEvent.id).where(PaymentEvent.event_hash == superseding_hash)
    ) is not None:
        return
    order_id = None
    if order_uuid is not None:
        order_id = await db.scalar(select(Order.id).where(Order.id == order_uuid))
    db.add(
        new_payment_event(
            replace(event_data, event_hash=superseding_hash),
            processing_status="rejected",
            order_id=order_id,
            error_code="payment_belongs_to_another_order",
            error_detail=(
                f"Supersedes duplicate event {stale.id}: the provider payment "
                "belongs to another reference"
            ),
        )
    )
    await db.commit()


def _is_retryable_database_error(error: DBAPIError) -> bool:
    sqlstate = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)
    return sqlstate in RETRYABLE_SQLSTATES


async def _read_webhook_body(request: Request) -> bytes:
    """Read the body, counting the bytes received rather than Content-Length."""
    body = bytearray()
    async for chunk in request.stream():
        # Check before copying: one large chunk must not grow the buffer first.
        if len(body) + len(chunk) > MAX_WEBHOOK_BODY_BYTES:
            logger.warning("Prodamus webhook: body over %s bytes", MAX_WEBHOOK_BODY_BYTES)
            raise HTTPException(status_code=413, detail="Payload too large")
        body.extend(chunk)
    return bytes(body)


def _is_demo_payment_payload(payload: dict[str, Any]) -> bool:
    return str(payload.get("demo_mode", "")).strip().lower() in {"1", "true"}


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
    if tariff not in SELLABLE_TARIFFS:
        raise HTTPException(status_code=400, detail="Invalid tariff")
    price = float(course.price_self if tariff == "self" else course.price_support)
    course_name = receipt_item_name(course.title, course.access_days)
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
    order_reference: str = "",
) -> str:
    """One attempt at recording the purchase in its own transaction.

    The purchase and its notification are committed atomically. External
    delivery is handled later by the outbox worker.
    """
    webhook_email = _webhook_email_or_none(payload.get("customer_email"))
    reference = _reference_identity(order_reference)
    notified_kopecks = parse_amount_kopecks(payload.get("sum"))
    async with async_session_maker() as db:
        existing_event = await db.scalar(
            select(PaymentEvent).where(PaymentEvent.event_hash == event_data.event_hash)
        )
        if existing_event is not None:
            if existing_event.processing_status not in {"processed", "duplicate", "financial_incident"}:
                raise HTTPException(status_code=422, detail=existing_event.error_detail or "Payment was rejected")
            if existing_event.processing_status == "duplicate":
                # An older version stored duplicates without checking that the
                # payment belongs to the reference named; this one checks them
                # again. Processed and incident events are bindings themselves.
                binding = await _payment_binding(
                    db,
                    payment_key,
                    reference,
                    notified_kopecks,
                    await db.scalar(select(Purchase).where(Purchase.payment_id == payment_key)),
                )
                if binding.status != "same":
                    await _supersede_duplicate_event(db, existing_event, event_data, order_uuid)
                    logger.error("Prodamus webhook: stored duplicate names another reference")
                    raise HTTPException(status_code=422, detail="Payment belongs to another order")
            return webhook_email or ""

        # Read before any lock: a purchase found here is committed history.
        existing_pay = await db.execute(select(Purchase).where(Purchase.payment_id == payment_key))
        existing_purchase = existing_pay.scalars().first()

        order: Order | None = None
        email_differs = False
        if order_uuid is not None:
            # Lock the order before anything that references it is written, so
            # two deliveries for one order queue here. FOR NO KEY UPDATE, not
            # FOR UPDATE: it does not block the FOR KEY SHARE that foreign-key
            # checks take, so a refund recording an event for this order, which
            # holds its purchase, cannot form a lock cycle with us. A missing
            # order is rejected before a dangling foreign key is ever flushed.
            order_result = await db.execute(
                select(Order).where(Order.id == order_uuid).with_for_update(key_share=True)
            )
            order = order_result.scalar_one_or_none()
            if order is None:
                raise HTTPException(status_code=422, detail="Order not found")
            course_id_uuid = order.course_id
            tariff = order.tariff

        # A provider payment belongs to one reference. Deliveries of the same
        # payment id queue here, whatever they name, and each one reads the
        # binding a concurrent one committed (a purchase or an incident).
        await _lock_provider_payment(db, payment_key)
        binding = await _payment_binding(
            db, payment_key, reference, notified_kopecks, existing_purchase
        )
        if binding.status == "other":
            logger.error("Prodamus webhook: known payment for another reference")
            raise HTTPException(status_code=422, detail="Payment belongs to another order")
        if binding.status == "same" and binding.purchase_id is not None:
            payment_event = new_payment_event(event_data, order_id=order_uuid)
            db.add(payment_event)
            payment_event.purchase_id = binding.purchase_id
            payment_event.processing_status = "duplicate"
            payment_event.processed_at = datetime.utcnow()
            await db.commit()
            return webhook_email or ""
        # Otherwise the payment is new, or a redelivery of an incident for this
        # order, which the paid-order check below records as a duplicate.

        payment_event = new_payment_event(event_data, order_id=order_uuid)
        db.add(payment_event)

        if course_id_uuid is None or tariff is None:
            raise HTTPException(status_code=422, detail="Invalid order_id")
        # A legacy reference names its own tariff, so a hand-crafted payform link
        # could still buy a discontinued one. Orders were validated at checkout.
        if order is None and tariff not in SELLABLE_TARIFFS:
            logger.error("Prodamus webhook: legacy reference for unsellable tariff=%s", tariff)
            raise HTTPException(status_code=422, detail="Tariff not sellable")

        if order is not None:
            # The signed payment belongs to the order, so access goes to the email
            # given at checkout even if the buyer typed another one on the payform.
            # Orders created before email normalization may keep mixed case.
            customer_email = order.customer_email.strip().lower()
            email_differs = webhook_email is not None and webhook_email != customer_email
        elif webhook_email is None:
            raise HTTPException(status_code=422, detail="customer_email is required")
        else:
            customer_email = webhook_email

        customer_phone = _webhook_phone_or_none(payload.get("customer_phone"))
        if customer_phone is None and order is not None:
            # The payform sent no usable phone: keep the one typed at checkout.
            customer_phone = order.customer_phone

        course_result = await db.execute(select(Course).where(Course.id == course_id_uuid))
        course = course_result.scalars().first()
        if not course or (order is None and not course.is_published):
            logger.error("Prodamus webhook: course unavailable %s", course_id_uuid)
            raise HTTPException(status_code=422, detail="Course not found")

        paid_kopecks = parse_amount_kopecks(payload.get("sum"))

        expected_kopecks = (
            order.amount_kopecks
            if order is not None
            else int(course.price_self if tariff == "self" else course.price_support) * 100
        )
        if paid_kopecks is None or abs(paid_kopecks - expected_kopecks) > 2:
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

        if order is not None:
            original_purchase = await db.scalar(select(Purchase).where(Purchase.order_id == order.id))
            if original_purchase is not None:
                if original_purchase.payment_id == payment_key:
                    payment_event.purchase_id = original_purchase.id
                    payment_event.processing_status = "duplicate"
                    payment_event.processed_at = datetime.utcnow()
                    await db.commit()
                    return customer_email
                # The binding read under the provider payment lock tells the
                # first incident from its repeat: it resolves the payment id
                # under either field order, where the raw order_id may be the
                # order reference shared by every payment for this order.
                repeated_incident = binding.status == "same"
                payment_event.purchase_id = original_purchase.id
                payment_event.processing_status = (
                    "duplicate" if repeated_incident else "financial_incident"
                )
                payment_event.error_code = "duplicate_order_payment"
                payment_event.error_detail = "Additional payment for an already paid order; reconcile with provider"
                payment_event.processed_at = datetime.utcnow()
                if not repeated_incident:
                    incident_key = hashlib.sha256(payment_key.encode("utf-8")).hexdigest()
                    await enqueue_owner_telegram_alert(
                        db,
                        kind="owner_payment_incident",
                        text=f"⚠️ Повторная оплата заказа {order.id}: {format_rub(paid_kopecks)}. Платёж {payment_key}. Доступ повторно не выдан; требуется сверка и решение о возврате.",
                        dedupe_key=f"payment:{incident_key}:incident",
                    )
                await db.commit()
                return customer_email

        # A signed payment proves who paid, not who owns an existing account:
        # only an account created by this payment takes the phone.
        user, is_new_user = await _get_or_create_user(db, customer_email, customer_phone)
        if is_new_user and order is not None:
            # The account is born from this guest checkout: keep its consent proof.
            user.offer_accepted_at = order.offer_accepted_at
            user.personal_data_consent_at = order.personal_data_consent_at
            user.consent_version = order.consent_version

        # Two orders of one buyer for one course can be confirmed at the same
        # moment; without this lock both read the same current expiry and one
        # paid period is lost. The clock is read after the lock, so the access
        # granted by the transaction we waited for is already current.
        await AccessService.lock_course_access(db, user.id, course.id)
        paid_at = datetime.utcnow()
        access_days = order.access_days if order is not None else settings.COURSE_ACCESS_DAYS
        # An early renewal adds the paid days on top of access that is still running,
        # like a manual grant does, instead of restarting the period from today.
        current_access = await AccessService.get_active_entitlement(
            db, user.id, course.id, now=paid_at
        )
        access_base = max(paid_at, current_access.expires_at) if current_access else paid_at
        expires_at = access_base + timedelta(days=access_days)

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
        if user.email_verified_at is None:
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
        if user.email_verified_at is not None and user.telegram_id is not None and settings.TELEGRAM_BOT_TOKEN:
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
                        f"до {format_msk_datetime(expires_at)}.{support_note}"
                    )
                },
                dedupe_key=f"payment:{dedupe_hash}:access:telegram",
            )
        await enqueue_owner_telegram_alert(
            db,
            kind="owner_payment_alert",
            text=(
                "💰 Новая оплата\n"
                f"Сумма: {format_rub(paid_kopecks)}\n"
                f"Курс: {course.title}\n"
                f"Тариф: {TARIFF_LABELS.get(tariff, tariff)}\n"
                f"Email: {customer_email}\n"
                + (
                    f"Email в форме оплаты другой: {webhook_email}. Доступ выдан на email заказа.\n"
                    if email_differs
                    else ""
                )
                + f"Заказ: {order_reference or '—'}"
            ),
            dedupe_key=f"payment:{dedupe_hash}:owner",
        )
        if order is not None:
            order.status = "paid"
            order.paid_at = paid_at
            if order.user_id is None:
                # A guest checkout: link the order to the account that got access.
                order.user_id = user.id
        await AnalyticsService.record_event(
            db,
            event_id=_purchase_confirmed_event_id(payment_key),
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


async def _record_rejected_webhook(
    event_data: PaymentEventData,
    payload: dict[str, Any],
    *,
    processing_status: str,
    error_code: str,
    error_detail: str,
    order_id: UUID | None = None,
    payment_key: str | None = None,
) -> None:
    """Record a signed webhook that was not processed and alert the owner once.

    The alert is keyed by the normalised provider payment id when the
    notification has one (not the event hash, which changes with Prodamus'
    ``attempt`` counter, and not the raw order_id, which holds the order
    reference in the old field order), so retries do not spam.
    """
    try:
        await record_terminal_payment_event(
            event_data,
            processing_status=processing_status,
            error_code=error_code,
            error_detail=error_detail,
            order_id=order_id,
        )
    except IntegrityError:
        # A concurrent delivery of the same notification recorded it first.
        logger.info("Prodamus webhook: rejected event already recorded")
    identity = payment_key or event_data.external_event_id or event_data.order_reference
    if not identity:
        # Without ids, key on the body minus the per-delivery retry counter.
        stable_payload = {key: value for key, value in payload.items() if key != "attempt"}
        identity = json.dumps(
            stable_payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")
        )
    identity_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    form_email = str(payload.get("customer_email") or "").strip()[:320]
    order_reference = event_data.order_reference or event_data.external_event_id or "—"
    # Support is asked about the checkout email's account, so a notification
    # that names an order shows that email (legacy callbacks swap the fields).
    matched_order_id = (
        order_id
        or _parse_persisted_order_id(event_data.order_reference or "")
        or _parse_persisted_order_id(event_data.external_event_id or "")
    )
    async with async_session_maker() as db:
        email_lines = await payment_alert_email_lines(db, matched_order_id, form_email)
        if processing_status == "ignored":
            # Declines and cancellations: no money was taken.
            text = (
                f"ℹ️ Неуспешная попытка оплаты (статус: {event_data.event_type})\n"
                + email_lines
                + f"Заказ: {order_reference}"
            )
        else:
            amount = (
                format_rub(event_data.amount_kopecks)
                if event_data.amount_kopecks is not None
                else "—"
            )
            text = (
                f"⚠️ Платёж не обработан: {error_code}\n"
                f"Сумма: {amount}\n"
                + email_lines
                + f"Заказ: {order_reference}"
            )
        try:
            await enqueue_owner_telegram_alert(
                db,
                kind="owner_payment_rejected",
                text=text,
                dedupe_key=f"payment-rejected:{identity_hash}:{error_code}",
            )
            await db.commit()
        except IntegrityError:
            # A concurrent delivery queued the same alert; keep the caller's 422.
            await db.rollback()


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
    # Reject unsigned requests before spending any work on the body.
    signature = request.headers.get("Sign", "")
    if not signature:
        logger.warning("Prodamus webhook: no Sign header")
        raise HTTPException(status_code=400, detail="Missing signature")

    # The body is parsed before the signature can be checked, so cap its size.
    body = await _read_webhook_body(request)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = json.loads(body)
        except (ValueError, RecursionError):
            logger.warning("Prodamus webhook: unparseable JSON body")
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        # Prodamus posts multipart/form-data with bracket keys and signs the
        # nested PHP-style structure, not the flat field names.
        async def receive_read_body() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        form = await Request(request.scope, receive_read_body).form()
        payload = nest_form_fields(form.multi_items())

    correlation_id = getattr(request.state, "correlation_id", None)
    if not ProdamusService.verify_signature(payload, signature, correlation_id=correlation_id):
        logger.warning("Prodamus webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_data = build_payment_event_data(payload)
    provider_order_id_raw = str(payload.get("order_id", "")).strip()
    merchant_reference_raw = str(payload.get("order_num", "")).strip()
    # The normalised provider payment id keys the owner's rejection alert: the
    # same payment shares one key under either field order.
    alert_payment_key = (
        _resolve_payment_key(provider_order_id_raw, merchant_reference_raw)
        if provider_order_id_raw
        else None
    )
    if _is_demo_payment_payload(payload) and not ProdamusService.demo_payments_allowed():
        # Prodamus signs demo webhooks with the regular secret (observed
        # 2026-10-31), so the signature alone cannot stop a test payment from
        # granting access on a live shop.
        await _record_rejected_webhook(
            event_data,
            payload,
            processing_status="rejected",
            error_code="demo_payment",
            error_detail="Demo payment webhook while demo payments are disabled",
            payment_key=alert_payment_key,
        )
        logger.warning("Prodamus webhook: demo payment rejected")
        raise HTTPException(status_code=422, detail="Demo payment")
    status_verdict = _payment_status_verdict(payload)
    if status_verdict == "contradictory":
        # Money may or may not have been taken: never grant access, let the
        # owner reconcile with the provider.
        await _record_rejected_webhook(
            event_data,
            payload,
            processing_status="rejected",
            error_code="contradictory_payment_status",
            error_detail="Signed webhook carried contradictory payment status fields",
            payment_key=alert_payment_key,
        )
        logger.error("Prodamus webhook: contradictory payment status fields")
        raise HTTPException(status_code=422, detail="Contradictory payment status")
    if status_verdict != "success":
        await _record_rejected_webhook(
            event_data,
            payload,
            processing_status="ignored",
            error_code="payment_not_successful",
            error_detail="Signed webhook did not contain a successful payment status",
            payment_key=alert_payment_key,
        )
        logger.warning("Prodamus webhook: non-success payment payload")
        raise HTTPException(status_code=422, detail="Payment is not successful")

    if not provider_order_id_raw:
        await _record_rejected_webhook(
            event_data,
            payload,
            processing_status="rejected",
            error_code="missing_provider_order_id",
            error_detail="Prodamus callback did not contain order_id",
        )
        logger.error("Prodamus webhook: missing provider order_id")
        raise HTTPException(status_code=422, detail="Missing provider order id")
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
        await _record_rejected_webhook(
            event_data,
            payload,
            processing_status="rejected",
            error_code="invalid_order_reference",
            error_detail="Order reference has an unsupported format",
            payment_key=alert_payment_key,
        )
        logger.error("Prodamus webhook: invalid merchant order reference")
        raise HTTPException(status_code=422, detail="Invalid order reference")

    course_id_uuid, tariff = parsed if parsed else (None, None)
    payment_key = _resolve_payment_key(
        provider_order_id_raw,
        merchant_reference_raw,
    )
    try:
        # A persisted order already knows its buyer; only a legacy reference
        # takes the email from the payform.
        if order_uuid is None:
            _normalize_email(payload.get("customer_email"))
    except HTTPException as exc:
        await _record_rejected_webhook(
            event_data,
            payload,
            processing_status="rejected",
            error_code="invalid_customer_email",
            error_detail=str(exc.detail),
            order_id=order_uuid,
            payment_key=payment_key,
        )
        raise

    # Record the purchase, retrying once. A concurrent first-time buyer can hit a
    # users.email unique collision (two payments, same brand-new email): the racing
    # request commits the user, and the retry then finds it and inserts only the
    # Purchase — so a distinct second payment is never silently dropped. A genuine
    # duplicate payment_id short-circuits at the existing-purchase check. A
    # deadlock or serialization failure aborted the whole transaction in favour
    # of a concurrent one and is retried the same way.
    for attempt in range(2):
        try:
            await _record_purchase_once(
                payment_key,
                course_id_uuid,
                tariff,
                payload,
                event_data,
                order_uuid,
                order_reference=order_reference_raw,
            )
            break
        except HTTPException as exc:
            error_code = str(exc.detail).lower().replace(" ", "_")[:64]
            await _record_rejected_webhook(
                event_data,
                payload,
                processing_status="rejected",
                error_code=error_code,
                error_detail=str(exc.detail),
                order_id=order_uuid,
                payment_key=payment_key,
            )
            raise
        except DBAPIError as exc:
            if not isinstance(exc, IntegrityError) and not _is_retryable_database_error(exc):
                raise
            if attempt == 0:
                continue
            async with async_session_maker() as db:
                done = await db.scalar(select(Purchase).where(Purchase.payment_id == payment_key))
                # Answer success only for a notification proven processed: its
                # payment is recorded, and bound to the reference it names.
                if done is not None and (
                    await _payment_binding(
                        db,
                        payment_key,
                        _reference_identity(order_reference_raw),
                        parse_amount_kopecks(payload.get("sum")),
                        done,
                    )
                ).status == "same":
                    logger.info("Prodamus webhook duplicate payment_key=%s", payment_key)
                    return {"status": "ok"}
            logger.error("Prodamus webhook: unresolved database error payment_key=%s", payment_key)
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

    @field_validator("*", mode="before")
    @classmethod
    def drop_unusable_attribution(cls, value: Any) -> str | None:
        return clean_attribution_value(value)


def _none_if_invalid(value: Any, handler: ValidatorFunctionWrapHandler) -> Any:
    """A malformed part of optional attribution must not block a checkout."""
    try:
        return handler(value)
    except ValidationError:
        return None


class CheckoutAttribution(BaseModel):
    anonymous_id: Annotated[UUID | None, WrapValidator(_none_if_invalid)] = None
    first_touch: Annotated[AttributionTouch | None, WrapValidator(_none_if_invalid)] = None
    last_touch: Annotated[AttributionTouch | None, WrapValidator(_none_if_invalid)] = None


OptionalAttribution = Annotated[CheckoutAttribution | None, WrapValidator(_none_if_invalid)]


class PaymentLinkRequest(BaseModel):
    course_id: str
    tariff: str  # only SELLABLE_TARIFFS; others get 400 "Invalid tariff"
    customer_email: str | None = None
    customer_phone: str | None = None
    attribution: OptionalAttribution = None


class GuestPaymentLinkRequest(BaseModel):
    course_id: str
    tariff: str  # only SELLABLE_TARIFFS; others get 400 "Invalid tariff"
    customer_email: EmailStr
    customer_phone: str | None = None
    attribution: OptionalAttribution = None
    # Both must be true; checked in the endpoint to return a readable Russian 422.
    offer_accepted: bool = False
    personal_data_consent: bool = False


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
    require_consent(data.offer_accepted, data.personal_data_consent)
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
            consented_at=datetime.utcnow(),
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
async def get_order_status(order_id: str, token: str) -> dict[str, str | int | float]:
    order_uuid = _parse_persisted_order_id(order_id)
    if order_uuid is None:
        raise HTTPException(status_code=404, detail="Order not found")
    async with async_session_maker() as db:
        result = await db.execute(select(Order).where(Order.id == order_uuid))
        order = result.scalar_one_or_none()
    supplied_hash = _hash_status_token(token)
    if order is None or not hmac.compare_digest(order.status_token_hash, supplied_hash):
        raise HTTPException(status_code=404, detail="Order not found")
    # The token sits in the success-page URL (browser history, logs), so it only
    # works for a fixed time after checkout; afterwards it reads as unknown.
    if order.created_at < datetime.utcnow() - ORDER_STATUS_TOKEN_TTL:
        raise HTTPException(status_code=404, detail="Order not found")
    # Order snapshot, not the current course price: the success page reports it
    # to Metrika as purchase revenue.
    return {
        "status": order.status,
        "amount": order.amount_kopecks / 100,
        "currency": order.currency,
        "course_id": str(order.course_id),
        "course_title": order.course_title,
        "tariff": order.tariff,
        # Signed deep link parameter for the support bot (t.me/<bot>?start=...).
        "support_start": issue_order_start_param(order.id),
    }
