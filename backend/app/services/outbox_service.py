"""Transactional helpers for durable notification delivery."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.outbox import DeliveryAttempt, OutboxMessage
from app.services.email_service import EmailService


TELEGRAM_API_TIMEOUT_SECONDS = 10.0


async def _telegram_request(method: str, payload: dict) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Telegram bot is not configured")
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"
    async with httpx.AsyncClient(timeout=TELEGRAM_API_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload)
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError(f"Telegram API rejected {method}")


async def send_telegram_message(recipient: str, text: str) -> None:
    await _telegram_request("sendMessage", {"chat_id": recipient, "text": text})


async def remove_telegram_group_member(group_id: str, user_id: str) -> None:
    # Ban + immediate unban removes the current membership but lets the student
    # join again after a future support entitlement is granted.
    await _telegram_request("banChatMember", {"chat_id": group_id, "user_id": user_id})
    await _telegram_request(
        "unbanChatMember",
        {"chat_id": group_id, "user_id": user_id, "only_if_banned": True},
    )


def enqueue_outbox_message(
    db: AsyncSession,
    *,
    kind: str,
    recipient: str,
    payload: dict,
    dedupe_key: str,
    channel: str = "email",
) -> OutboxMessage:
    message = OutboxMessage(
        kind=kind,
        channel=channel,
        recipient=recipient,
        payload=payload,
        dedupe_key=dedupe_key,
        status="pending",
    )
    db.add(message)
    return message


async def deliver_outbox_message(message: OutboxMessage) -> None:
    if message.channel == "telegram":
        if message.kind == "telegram_group_remove":
            await remove_telegram_group_member(
                str(message.payload["group_id"]), message.recipient
            )
        else:
            await send_telegram_message(message.recipient, message.payload["text"])
        return
    if message.channel != "email":
        raise ValueError(f"Unsupported outbox channel: {message.channel}")
    if message.kind == "account_activation":
        await EmailService.send_account_activation(
            message.recipient,
            message.payload["activation_url"],
            message.payload["course_title"],
        )
        return
    if message.kind == "access_granted":
        await EmailService.send_access_granted(
            message.recipient,
            message.payload["login_url"],
            message.payload["course_title"],
        )
        return
    if message.kind in {"certificate_issued", "certificate_reissue"}:
        await EmailService.send_certificate_link(
            message.recipient,
            message.payload["student_name"],
            message.payload["course_title"],
            message.payload["certificate_number"],
            message.payload["verify_url"],
        )
        return
    if message.kind == "access_expiry_reminder":
        await EmailService.send_access_expiry_reminder(
            message.recipient,
            message.payload["course_title"],
            int(message.payload["days"]),
            message.payload["expires_at"],
        )
        return
    if message.kind == "access_expired":
        await EmailService.send_access_expired(
            message.recipient, message.payload["course_title"]
        )
        return
    raise ValueError(f"Unsupported outbox kind: {message.kind}")


async def process_outbox_batch(
    db: AsyncSession,
    *,
    deliver: Callable[[OutboxMessage], Awaitable[None]] = deliver_outbox_message,
    limit: int = 50,
) -> int:
    """Claim and deliver a bounded batch, recording every attempt."""
    now = datetime.utcnow()
    stale_lock = now - timedelta(minutes=10)
    result = await db.execute(
        select(OutboxMessage)
        .where(
            or_(
                and_(
                    OutboxMessage.status.in_(("pending", "retry")),
                    OutboxMessage.next_attempt_at <= now,
                ),
                and_(
                    OutboxMessage.status == "processing",
                    OutboxMessage.locked_at <= stale_lock,
                ),
            )
        )
        .order_by(OutboxMessage.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    messages = list(result.scalars().all())

    # Claim the complete selected batch while every row is still locked.  A
    # commit inside this loop would release the locks for the rows that have
    # not been marked yet, allowing another worker to deliver them as well.
    for message in messages:
        message.status = "processing"
        message.locked_at = now
        message.attempts += 1
    await db.commit()

    for message in messages:
        try:
            await deliver(message)
        except Exception as exc:
            error = str(exc)[:2000]
            db.add(
                DeliveryAttempt(
                    outbox_message_id=message.id,
                    attempt_number=message.attempts,
                    status="failed",
                    error=error,
                )
            )
            message.status = (
                "dead_letter" if message.attempts >= message.max_attempts else "retry"
            )
            message.last_error = error
            message.locked_at = None
            message.next_attempt_at = datetime.utcnow() + timedelta(
                seconds=min(60 * (2 ** message.attempts), 3600)
            )
        else:
            db.add(
                DeliveryAttempt(
                    outbox_message_id=message.id,
                    attempt_number=message.attempts,
                    status="sent",
                )
            )
            message.status = "sent"
            message.sent_at = datetime.utcnow()
            message.last_error = None
            message.locked_at = None
        await db.commit()

    return len(messages)
