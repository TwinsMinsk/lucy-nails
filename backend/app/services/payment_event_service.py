"""Build and persist privacy-safe payment event records."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.order import Order
from app.models.payment_event import PaymentEvent

# Kopecks are stored in PostgreSQL integer columns.
MAX_AMOUNT_KOPECKS = 2**31 - 1


def parse_amount_kopecks(raw: Any) -> int | None:
    """Parse a Prodamus ``sum`` into kopecks with decimal arithmetic.

    A dot or a comma separates the kopecks. A missing, malformed, non-finite,
    negative or out-of-range value gives None. A fraction of a kopeck, which
    Prodamus does not send, is rounded half up.
    """
    if raw is None:
        return None
    try:
        amount = Decimal(str(raw).strip().replace(",", "."))
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount < 0:
        return None
    kopecks = amount * 100
    if kopecks > MAX_AMOUNT_KOPECKS:
        return None
    return int(kopecks.quantize(Decimal(1), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class PaymentEventData:
    event_hash: str
    external_event_id: str | None
    order_reference: str | None
    event_type: str
    amount_kopecks: int | None
    currency: str | None
    sanitized_payload: dict[str, str]


def build_payment_event_data(payload: dict[str, Any]) -> PaymentEventData:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def clean(key: str, limit: int = 255) -> str | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        return str(value).strip()[:limit]

    # Prodamus names these fields from its own perspective: ``order_id`` is
    # the provider payment/order identifier, while ``order_num`` is the
    # merchant reference supplied when the payment link was created.
    external_event_id = clean("order_id")
    order_reference = clean("order_num")
    event_type = (
        clean("payment_status", 64)
        or clean("status", 64)
        or clean("result", 64)
        or "unknown"
    ).lower()
    amount_kopecks = parse_amount_kopecks(payload.get("sum"))
    currency = clean("currency", 8)
    sanitized_payload = {
        key: value
        for key in ("order_id", "order_num", "payment_status", "status", "result", "sum", "currency")
        if (value := clean(key)) is not None
    }
    return PaymentEventData(
        event_hash=event_hash,
        external_event_id=external_event_id,
        order_reference=order_reference,
        event_type=event_type,
        amount_kopecks=amount_kopecks,
        currency=currency.upper() if currency else None,
        sanitized_payload=sanitized_payload,
    )


def new_payment_event(
    data: PaymentEventData,
    *,
    processing_status: str = "received",
    order_id: UUID | None = None,
    purchase_id: UUID | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
) -> PaymentEvent:
    terminal = processing_status != "received"
    return PaymentEvent(
        provider="prodamus",
        event_hash=data.event_hash,
        external_event_id=data.external_event_id,
        order_reference=data.order_reference,
        order_id=order_id,
        purchase_id=purchase_id,
        event_type=data.event_type,
        processing_status=processing_status,
        amount_kopecks=data.amount_kopecks,
        currency=data.currency,
        sanitized_payload=data.sanitized_payload,
        error_code=error_code,
        error_detail=(error_detail or "")[:1000] or None,
        processed_at=datetime.utcnow() if terminal else None,
    )


async def record_terminal_payment_event(
    data: PaymentEventData,
    *,
    processing_status: str,
    error_code: str,
    error_detail: str,
    order_id: UUID | None = None,
    purchase_id: UUID | None = None,
) -> None:
    async with async_session_maker() as db:
        existing = await db.scalar(
            select(PaymentEvent.id).where(PaymentEvent.event_hash == data.event_hash)
        )
        if existing is not None:
            return
        if order_id is not None and await db.scalar(
            select(Order.id).where(Order.id == order_id)
        ) is None:
            # A signed reference can name an order this database does not
            # have; order_reference keeps it for reconciliation instead of a
            # foreign key that cannot be stored.
            order_id = None
        db.add(
            new_payment_event(
                data,
                processing_status=processing_status,
                order_id=order_id,
                purchase_id=purchase_id,
                error_code=error_code,
                error_detail=error_detail,
            )
        )
        await db.commit()
