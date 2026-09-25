"""Build and persist privacy-safe payment event records."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.payment_event import PaymentEvent


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
    amount_kopecks: int | None = None
    try:
        amount_kopecks = int(round(float(str(payload.get("sum", "")).replace(",", ".")) * 100))
    except (TypeError, ValueError):
        pass
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
