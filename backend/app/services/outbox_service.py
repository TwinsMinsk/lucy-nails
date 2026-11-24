"""Transactional helpers for durable notification delivery."""

import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.outbox import DeliveryAttempt, OutboxMessage
from app.services.email_service import EmailService
from app.services.support_access_service import (
    has_active_support_entitlement,
    lock_support_membership_state,
)


TELEGRAM_API_TIMEOUT_SECONDS = 10.0
# A token inside a Telegram API URL (any shape, even one already rotated away)
# or on its own.
TELEGRAM_TOKEN_PATTERN = re.compile(
    r"""(?<=api\.telegram\.org/bot)[^/\s'"]+|\d{5,}:[A-Za-z0-9_-]{20,}"""
)
REDACTED = "[REDACTED]"
# A URL whose query carries a token: activation, password reset and login
# links. Anyone reading the database or a backup could use one that is still
# valid, so it is removed once the message no longer needs it.
SECRET_URL_PATTERN = re.compile(
    r"""https?://[^\s"'<>]*?[?&][^\s"'<>=&]*token=[^\s"'<>]*""",
    re.IGNORECASE,
)
# Statuses after which the worker never sends the message again by itself.
PAYLOAD_REDACTION_STATUSES = frozenset({"sent", "dead_letter"})


def redact_payload_secrets(value):
    """Return a copy of an outbox payload with every token-bearing URL replaced."""
    if isinstance(value, str):
        return SECRET_URL_PATTERN.sub(REDACTED, value)
    if isinstance(value, dict):
        return {key: redact_payload_secrets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_payload_secrets(item) for item in value]
    return value


def _unredacted_link(url: str) -> str:
    # A message whose link was removed (dead letter retried by hand) must not
    # send a broken link; the operator has to send a new one instead.
    if REDACTED in url:
        raise ValueError("The link of this message was removed after delivery; send a new one")
    return url


class TelegramApiError(RuntimeError):
    """Telegram call failure whose text is safe to store and log.

    The request URL contains the bot token, so httpx exceptions, whose text and
    attributes carry that URL, must not leave _telegram_request.

    ``status_code`` is the HTTP status (None when Telegram was not reached),
    ``description`` Telegram's own redacted explanation. ``transient`` marks a
    failure a later retry can fix: network trouble, 429 or a server error.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        description: str = "",
        transient: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.description = description
        self.transient = transient


def redact_telegram_token(text: str) -> str:
    if settings.TELEGRAM_BOT_TOKEN:
        text = text.replace(settings.TELEGRAM_BOT_TOKEN, REDACTED)
    return TELEGRAM_TOKEN_PATTERN.sub(REDACTED, text)


def _telegram_description(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    if not isinstance(body, dict):
        return ""
    return redact_telegram_token(str(body.get("description") or ""))[:200]


async def _telegram_request(method: str, payload: dict) -> Any:
    """Call the Bot API and return its ``result``; raise TelegramApiError otherwise."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Telegram bot is not configured")
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"
    try:
        async with httpx.AsyncClient(timeout=TELEGRAM_API_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError as exc:
        raise TelegramApiError(
            f"Telegram API {method} failed: {type(exc).__name__}", transient=True
        ) from None
    if not response.is_success:
        description = _telegram_description(response)
        raise TelegramApiError(
            f"Telegram API {method} failed with HTTP {response.status_code}"
            + (f": {description}" if description else ""),
            status_code=response.status_code,
            description=description,
            transient=response.status_code == 429 or response.status_code >= 500,
        )
    try:
        body = response.json()
    except ValueError:
        raise TelegramApiError(
            f"Telegram API {method} returned an unreadable response", transient=True
        ) from None
    if not isinstance(body, dict) or not body.get("ok"):
        raise TelegramApiError(f"Telegram API rejected {method}")
    return body.get("result")


async def call_telegram_api(method: str, payload: dict) -> Any:
    """Bot API call with the outbox's token redaction and timeout.

    Only the live help desk conversation (app/services/telegram_helpdesk_service.py)
    calls Telegram outside the outbox; everything else enqueues.
    """
    return await _telegram_request(method, payload)


async def send_telegram_message(
    recipient: str, text: str, *, message_thread_id: int | None = None
) -> None:
    payload: dict[str, Any] = {"chat_id": recipient, "text": text}
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
    await _telegram_request("sendMessage", payload)


async def remove_telegram_group_member(group_id: str, user_id: str) -> None:
    await _telegram_request("banChatMember", {"chat_id": group_id, "user_id": user_id})


async def restore_telegram_group_member(group_id: str, user_id: str) -> None:
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


def format_rub(kopecks: int) -> str:
    """Format an amount in kopecks as '5 900 ₽' (kopecks shown only when present)."""
    rubles, remainder = divmod(kopecks, 100)
    amount = f"{rubles:,}".replace(",", " ")
    if remainder:
        amount += f",{remainder:02d}"
    return f"{amount} ₽"


def owner_alert_target() -> tuple[str, int | None] | None:
    """Chat (and forum topic) that receives owner alerts, or None when off.

    With the help desk group and its «Оплаты» topic configured, alerts go there
    so both operators see them; otherwise to the owner's own chat.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    if (
        settings.TELEGRAM_HELPDESK_CHAT_ID is not None
        and settings.TELEGRAM_HELPDESK_ALERTS_TOPIC_ID is not None
    ):
        return (
            str(settings.TELEGRAM_HELPDESK_CHAT_ID),
            settings.TELEGRAM_HELPDESK_ALERTS_TOPIC_ID,
        )
    if settings.TELEGRAM_OWNER_CHAT_ID is not None:
        return str(settings.TELEGRAM_OWNER_CHAT_ID), None
    return None


async def enqueue_owner_telegram_alert(
    db: AsyncSession,
    *,
    kind: str,
    text: str,
    dedupe_key: str,
) -> bool:
    """Queue a Telegram message to the shop owner once per dedupe key.

    Does nothing unless the bot token and an alert chat (see
    owner_alert_target) are set. The message joins the caller's transaction
    (transactional outbox).
    """
    target = owner_alert_target()
    if target is None:
        return False
    existing = await db.scalar(
        select(OutboxMessage.id).where(OutboxMessage.dedupe_key == dedupe_key)
    )
    if existing is not None:
        return False
    recipient, topic_id = target
    payload: dict[str, Any] = {"text": text}
    if topic_id is not None:
        payload["message_thread_id"] = topic_id
    enqueue_outbox_message(
        db,
        kind=kind,
        channel="telegram",
        recipient=recipient,
        payload=payload,
        dedupe_key=dedupe_key,
    )
    return True


async def deliver_outbox_message(message: OutboxMessage) -> None:
    if message.channel == "telegram":
        if message.kind == "telegram_group_remove":
            await remove_telegram_group_member(
                str(message.payload["group_id"]), message.recipient
            )
        elif message.kind == "telegram_group_restore":
            await restore_telegram_group_member(
                str(message.payload["group_id"]), message.recipient
            )
        else:
            topic_id = message.payload.get("message_thread_id")
            if topic_id is not None:
                await send_telegram_message(
                    message.recipient,
                    message.payload["text"],
                    message_thread_id=int(topic_id),
                )
            else:
                # Rows queued before alerts could target a topic carry text only.
                await send_telegram_message(message.recipient, message.payload["text"])
        return
    if message.channel != "email":
        raise ValueError(f"Unsupported outbox channel: {message.channel}")
    if message.kind == "account_activation":
        await EmailService.send_account_activation(
            message.recipient,
            _unredacted_link(message.payload["activation_url"]),
            message.payload["course_title"],
            message.payload.get("expires_at"),
        )
        return
    if message.kind == "email_verification":
        await EmailService.send_email_verification(
            message.recipient, _unredacted_link(message.payload["activation_url"])
        )
        return
    if message.kind == "password_reset":
        await EmailService.send_password_reset(
            message.recipient, _unredacted_link(message.payload["reset_url"])
        )
        return
    if message.kind == "access_granted":
        await EmailService.send_access_granted(
            message.recipient,
            message.payload["login_url"],
            message.payload["course_title"],
            message.payload.get("expires_at"),
        )
        return
    if message.kind == "login_link":
        await EmailService.send_login_link(
            message.recipient, _unredacted_link(message.payload["login_url"])
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


async def _membership_message_is_obsolete(
    db: AsyncSession,
    message: OutboxMessage,
) -> bool:
    """Lock membership delivery and compare it with aggregate access state."""
    if message.kind not in {"telegram_group_remove", "telegram_group_restore"}:
        return False
    raw_user_id = message.payload.get("user_id")
    if not raw_user_id:
        # Legacy queued messages cannot be linked safely and keep their
        # original delivery semantics.
        return False
    try:
        user_id = UUID(str(raw_user_id))
    except ValueError:
        return False
    # This transaction lock is intentionally held through the external call
    # and its DeliveryAttempt commit. Entitlement mutations take the same lock,
    # so two workers cannot apply an older restore/remove after a newer state.
    await lock_support_membership_state(db, user_id)
    should_be_member = await has_active_support_entitlement(db, user_id)
    if message.kind == "telegram_group_remove":
        return should_be_member
    return not should_be_member


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
        skipped = False
        try:
            skipped = await _membership_message_is_obsolete(db, message)
            if not skipped:
                await deliver(message)
        except Exception as exc:
            # Redact first: truncation could cut a token past recognition.
            error = redact_telegram_token(str(exc))[:2000]
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
            # A retry still needs the link; a dead letter no longer does.
            if message.status in PAYLOAD_REDACTION_STATUSES:
                message.payload = redact_payload_secrets(message.payload)
        else:
            db.add(
                DeliveryAttempt(
                    outbox_message_id=message.id,
                    attempt_number=message.attempts,
                    status="skipped" if skipped else "sent",
                )
            )
            message.status = "sent"
            message.sent_at = datetime.utcnow()
            message.last_error = None
            message.locked_at = None
            message.payload = redact_payload_secrets(message.payload)
        await db.commit()

    return len(messages)
