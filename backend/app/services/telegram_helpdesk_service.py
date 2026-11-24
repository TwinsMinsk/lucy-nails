"""Telegram support bot: one implementation of update handling for both transports.

Customers write to the bot in a private chat. Each customer gets a forum
topic in the operators' private supergroup (TELEGRAM_HELPDESK_CHAT_ID); their
messages are copied into it and operator messages in the topic are copied
back. The webhook (app/api/telegram_webhook.py) and the local polling entry
point (app/bot/main.py) both call ``process_update``.

Exception to the outbox rule: operator replies and acknowledgements are part
of a live conversation, so this module calls the Bot API directly through
``outbox_service.call_telegram_api`` (same token redaction and timeout).

Privacy: message text and files are never stored, and a customer never gets
account, order or access data from the bot on the strength of a typed email;
that information goes to the operators' topic only.
"""

import logging
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.services.auth import BotAuthService
from app.core.config import settings
from app.models.order import Order
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.telegram_helpdesk import HelpdeskMessage, HelpdeskThread, TelegramUpdate
from app.models.user import User
from app.services import outbox_service
from app.services.access_service import AccessService
from app.services.email_service import format_msk_datetime
from app.services.outbox_service import TelegramApiError, format_rub
from app.services.support_links import (
    is_account_link_param,
    order_reference,
    verify_order_start_param,
)

logger = logging.getLogger(__name__)

# The address the site footer shows for support.
SUPPORT_EMAIL = "Luci4ek@gmail.com"
# Update types the handler uses; the webhook script and polling subscribe to these.
ALLOWED_UPDATES = ("message",)

FLOOD_LIMIT = 20
FLOOD_WINDOW = timedelta(minutes=1)
ACK_INTERVAL = timedelta(hours=3)
CARD_ORDER_LIMIT = 5
TOPIC_NAME_MAX_LENGTH = 128
PROCESSED_UPDATE_RETENTION = timedelta(days=7)

TO_OPERATORS = "to_operators"
TO_CUSTOMER = "to_customer"

# Message content copyMessage can relay; service messages carry none of these.
CONTENT_TYPES = (
    "text",
    "photo",
    "document",
    "voice",
    "video",
    "video_note",
    "sticker",
    "audio",
    "animation",
    "contact",
    "location",
    "venue",
    "poll",
    "dice",
)

ORDER_STATUS_LABELS = {"pending": "не оплачен", "paid": "оплачен"}

# --- Texts the customer sees -------------------------------------------------

GREETING_TEXT = (
    "Здравствуйте! Это поддержка школы Lucy Smirnova Nails.\n\n"
    "Напишите свой вопрос — об оплате, доступе к курсу или урокам, — "
    "и мы ответим здесь, в этом чате.\n\n"
    "Если вопрос об оплате или доступе, пришлите, пожалуйста, email, "
    "который указывали при покупке, — так мы быстрее найдём заказ."
)
ORDER_GREETING_TEXT = (
    "Здравствуйте! Это поддержка школы Lucy Smirnova Nails.\n\n"
    "Мы видим, с какого заказа вы пришли. Напишите, что случилось, — "
    "ответим здесь, в этом чате."
)
HELPDESK_OFF_TEXT = (
    "Здравствуйте! Это бот школы Lucy Smirnova Nails.\n\n"
    f"Поддержка сейчас отвечает по почте: {SUPPORT_EMAIL}. Напишите туда и укажите "
    "email, который указывали при покупке."
)
ACK_TEXT = "Спасибо! Сообщение передано в поддержку — ответим здесь, в этом чате."
ACK_ASK_EMAIL_TEXT = (
    ACK_TEXT + "\n\nЕсли вопрос об оплате или доступе, пришлите email, "
    "который указывали при покупке."
)
EMAIL_ACK_TEXT = "Спасибо, email передали в поддержку. Ответим здесь, в этом чате."
FLOOD_TEXT = (
    "Вы отправили много сообщений подряд. Подождите минуту — "
    "поддержка прочитает всё, что уже пришло."
)
RELAY_FAILED_TEXT = (
    "Не получилось передать сообщение в поддержку. Попробуйте ещё раз чуть позже "
    f"или напишите на почту {SUPPORT_EMAIL}."
)
LINK_PENDING_TEXT = "⏳ Проверяю данные..."

# --- Texts the operators see -------------------------------------------------

CLOSED_TEXT = "🔒 Тема закрыта. Если клиент напишет снова, она откроется сама."
REOPENED_TEXT = "🔓 Клиент написал снова — тема открыта."
BLOCKED_TEXT = (
    "⛔ Клиент заблокирован: его сообщения больше не будут приходить. "
    "Разблокировать — /unblock."
)
UNBLOCKED_TEXT = "✅ Клиент разблокирован."
BLOCKED_NOT_SENT_TEXT = (
    "⛔ Клиент заблокирован, сообщение не отправлено. Разблокировать — /unblock."
)
UNDELIVERED_UNREACHABLE_TEXT = (
    "⚠️ Сообщение не доставлено: клиент заблокировал бота или ещё не начинал с ним диалог."
)
UNDELIVERED_OTHER_TEXT = (
    "⚠️ Сообщение не доставлено клиенту: {reason}. Попробуйте отправить ещё раз."
)
OPERATOR_HELP_TEXT = (
    "Команды в теме клиента:\n"
    "/info — свежая карточка клиента\n"
    "/close — закрыть тему (новое сообщение клиента откроет её)\n"
    "/block — заблокировать клиента, /unblock — разблокировать\n"
    "/chatid — id чата и темы"
)

_email_adapter = TypeAdapter(EmailStr)


class HelpdeskTransientError(RuntimeError):
    """A failure a redelivery of the same update can fix (network, database)."""


def helpdesk_enabled() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN) and settings.TELEGRAM_HELPDESK_CHAT_ID is not None


def _bot_id() -> int | None:
    prefix = settings.TELEGRAM_BOT_TOKEN.split(":", 1)[0]
    return int(prefix) if prefix.isdigit() else None


async def _call(method: str, payload: dict) -> Any:
    return await outbox_service.call_telegram_api(method, payload)


async def _send_quietly(chat_id: int, text: str, *, topic_id: int | None = None) -> None:
    """Best-effort reply: never fails the update after its main effect happened."""
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if topic_id is not None:
        payload["message_thread_id"] = topic_id
    try:
        await _call("sendMessage", payload)
    except TelegramApiError as exc:
        logger.warning("Help desk: reply not sent: %s", exc)


async def _post_to_topic(thread: HelpdeskThread, text: str) -> None:
    """Post a notice operators must see; a temporary failure retries the update."""
    try:
        await _call(
            "sendMessage",
            {"chat_id": thread.chat_id, "message_thread_id": thread.topic_id, "text": text},
        )
    except TelegramApiError as exc:
        if exc.transient:
            raise
        logger.error("Help desk: notice not posted to topic: %s", exc)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, TelegramApiError):
        return exc.transient
    if isinstance(exc, (OperationalError, InterfaceError, PoolTimeoutError)):
        return True
    if isinstance(exc, DBAPIError):
        if exc.connection_invalidated:
            return True
        sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None) or ""
        return sqlstate in {"40P01", "40001"} or sqlstate.startswith("08")
    return isinstance(exc, (TimeoutError, ConnectionError))


async def _rollback_quietly(db: AsyncSession) -> None:
    try:
        await db.rollback()
    except Exception:
        logger.exception("Help desk: rollback failed")


async def _claim_update(db: AsyncSession, update_id: int) -> bool:
    inserted = await db.execute(
        pg_insert(TelegramUpdate)
        .values(update_id=update_id, received_at=datetime.utcnow())
        .on_conflict_do_nothing(index_elements=[TelegramUpdate.update_id])
        .returning(TelegramUpdate.update_id)
    )
    return inserted.scalar_one_or_none() is not None


async def process_update(db: AsyncSession, update: Any) -> bool:
    """Handle one raw Telegram update at most once; True when it was handled now.

    A malformed or unsupported update is ignored. Raises HelpdeskTransientError
    when a redelivery can help; the update is then not recorded as processed.
    Any other failure is logged and the update recorded, so a poison update is
    not redelivered forever.
    """
    if not isinstance(update, dict):
        return False
    update_id = update.get("update_id")
    if not isinstance(update_id, int) or isinstance(update_id, bool) or not 0 <= update_id < 2**63:
        return False
    try:
        # The insert waits for a concurrent delivery of the same update and
        # then finds its row: the update is handled exactly once.
        if not await _claim_update(db, update_id):
            await db.rollback()
            return False
        await _dispatch(db, update)
        await db.commit()
        return True
    except HelpdeskTransientError:
        await _rollback_quietly(db)
        raise
    except Exception as exc:
        await _rollback_quietly(db)
        if _is_transient(exc):
            raise HelpdeskTransientError(f"Telegram update {update_id}: {type(exc).__name__}") from exc
        logger.exception("Help desk: update %s could not be handled and is skipped", update_id)
    try:
        await _claim_update(db, update_id)
        await db.commit()
    except Exception as exc:
        await _rollback_quietly(db)
        raise HelpdeskTransientError(f"Telegram update {update_id}: not recorded") from exc
    return False


async def prune_processed_updates(db: AsyncSession, *, now: datetime) -> None:
    """Telegram stops redelivering after a day; old update ids are not needed."""
    await db.execute(
        delete(TelegramUpdate).where(TelegramUpdate.received_at < now - PROCESSED_UPDATE_RETENTION)
    )


# --- Dispatch ----------------------------------------------------------------


def _parse_command(message: dict) -> tuple[str | None, list[str]]:
    """("name", args) for a bot command, ("", []) for another bot's, (None, []) otherwise."""
    text = message.get("text")
    if not isinstance(text, str) or not text.startswith("/"):
        return None, []
    parts = text.split()
    name, _, mention = parts[0][1:].partition("@")
    own_username = settings.TELEGRAM_BOT_USERNAME.lstrip("@").lower()
    if mention and mention.lower() != own_username:
        return "", []
    return name.lower(), parts[1:]


def _content_type(message: dict) -> str | None:
    for key in CONTENT_TYPES:
        if message.get(key):
            return key
    return None


async def _dispatch(db: AsyncSession, update: dict) -> None:
    message = update.get("message")
    if not isinstance(message, dict):
        return
    chat = message.get("chat")
    sender = message.get("from")
    if not isinstance(chat, dict) or not isinstance(sender, dict):
        return
    chat_id = chat.get("id")
    if not isinstance(chat_id, int) or not isinstance(message.get("message_id"), int):
        return
    if sender.get("id") == _bot_id():
        return
    command, args = _parse_command(message)
    if command == "chatid":
        await _reply_chat_id(message)
        return
    if chat.get("type") == "private":
        if sender.get("is_bot") or not isinstance(sender.get("id"), int):
            return
        await _handle_customer(db, message, command, args)
        return
    if helpdesk_enabled() and chat_id == settings.TELEGRAM_HELPDESK_CHAT_ID:
        # An operator posting anonymously appears as GroupAnonymousBot on behalf
        # of the group itself; any other bot is ignored.
        sender_chat = message.get("sender_chat")
        anonymous_admin = isinstance(sender_chat, dict) and sender_chat.get("id") == chat_id
        if sender.get("is_bot") and not anonymous_admin:
            return
        await _handle_operator(db, message, command)


async def _reply_chat_id(message: dict) -> None:
    chat_id = message["chat"]["id"]
    text = f"ID чата: {chat_id}"
    topic_id = message.get("message_thread_id") if message.get("is_topic_message") else None
    if topic_id is not None:
        text += f"\nID темы: {topic_id}"
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if topic_id is not None:
        payload["message_thread_id"] = topic_id
    try:
        await _call("sendMessage", payload)
    except TelegramApiError as exc:
        if exc.transient:
            raise
        logger.warning("Help desk: /chatid reply not sent: %s", exc)


# --- Customer side -----------------------------------------------------------


def _display_name(sender: dict) -> str | None:
    parts = [
        str(sender.get(key)).strip()
        for key in ("first_name", "last_name")
        if sender.get(key) and str(sender.get(key)).strip()
    ]
    return " ".join(parts)[:255] or None


def _plain_email(message: dict) -> str | None:
    text = message.get("text")
    if not isinstance(text, str):
        return None
    candidate = text.strip()
    if not candidate or len(candidate) > 254 or any(char.isspace() for char in candidate):
        return None
    try:
        return str(_email_adapter.validate_python(candidate)).lower()
    except ValidationError:
        return None


async def _lock_thread(db: AsyncSession, sender: dict, now: datetime) -> HelpdeskThread:
    telegram_user_id = sender["id"]
    await db.execute(
        pg_insert(HelpdeskThread)
        .values(
            id=uuid.uuid4(),
            telegram_user_id=telegram_user_id,
            status="open",
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=[HelpdeskThread.telegram_user_id])
    )
    # One customer's updates are handled one at a time: no second topic, no
    # interleaved state.
    thread = await db.scalar(
        select(HelpdeskThread)
        .where(HelpdeskThread.telegram_user_id == telegram_user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    username = sender.get("username")
    thread.telegram_username = str(username)[:64] if username else None
    thread.display_name = _display_name(sender)
    await _sync_linked_account(db, thread)
    return thread


async def _sync_linked_account(db: AsyncSession, thread: HelpdeskThread) -> bool:
    """Link the thread to the site account this Telegram is connected to."""
    user_id = await db.scalar(
        select(User.id).where(User.telegram_id == thread.telegram_user_id)
    )
    if user_id is None or user_id == thread.user_id:
        return False
    thread.user_id = user_id
    return True


def _ack_text(thread: HelpdeskThread) -> str:
    if thread.user_id is None and thread.stated_email is None:
        return ACK_ASK_EMAIL_TEXT
    return ACK_TEXT


async def _handle_customer(
    db: AsyncSession, message: dict, command: str | None, args: list[str]
) -> None:
    sender = message["from"]
    chat_id = message["chat"]["id"]
    if not helpdesk_enabled():
        # No thread is stored while the help desk is off.
        if command == "start" and args and is_account_link_param(args[0]):
            await _link_account(chat_id, sender, args[0])
            return
        await _send_quietly(chat_id, HELPDESK_OFF_TEXT)
        return

    now = datetime.utcnow()
    thread = await _lock_thread(db, sender, now)
    if thread.status == "blocked":
        return
    if command == "start":
        await _handle_start(db, thread, chat_id, sender, args)
        return
    content_type = _content_type(message)
    if content_type is None:
        return
    if await _flood_exceeded(db, thread, now):
        if thread.flood_notice_at is None or now - thread.flood_notice_at >= FLOOD_WINDOW:
            thread.flood_notice_at = now
            await _send_quietly(chat_id, FLOOD_TEXT)
        return

    stated_email = _plain_email(message) if thread.user_id is None else None
    email_changed = stated_email is not None and stated_email != thread.stated_email
    if email_changed:
        thread.stated_email = stated_email

    try:
        topic_created = await _ensure_topic(db, thread)
        group_message_id = await _copy_to_topic(db, thread, message)
    except TelegramApiError as exc:
        if exc.transient:
            raise
        logger.error("Help desk: customer message not relayed: %s", exc)
        await _send_quietly(chat_id, RELAY_FAILED_TEXT)
        return

    db.add(
        HelpdeskMessage(
            thread_id=thread.id,
            direction=TO_OPERATORS,
            customer_message_id=message["message_id"],
            group_message_id=group_message_id,
            content_type=content_type,
            created_at=now,
        )
    )
    thread.last_customer_message_at = now
    if email_changed and not topic_created:
        await _refresh_topic(db, thread)

    if email_changed:
        thread.last_ack_at = now
        await _send_quietly(chat_id, EMAIL_ACK_TEXT)
    elif thread.last_ack_at is None or now - thread.last_ack_at >= ACK_INTERVAL:
        thread.last_ack_at = now
        await _send_quietly(chat_id, _ack_text(thread))


async def _flood_exceeded(db: AsyncSession, thread: HelpdeskThread, now: datetime) -> bool:
    recent = await db.scalar(
        select(func.count(HelpdeskMessage.id)).where(
            HelpdeskMessage.thread_id == thread.id,
            HelpdeskMessage.direction == TO_OPERATORS,
            HelpdeskMessage.created_at > now - FLOOD_WINDOW,
        )
    )
    return (recent or 0) >= FLOOD_LIMIT


async def _handle_start(
    db: AsyncSession,
    thread: HelpdeskThread,
    chat_id: int,
    sender: dict,
    args: list[str],
) -> None:
    param = args[0] if args else ""
    order_id = verify_order_start_param(param) if param else None
    if order_id is not None and await db.get(Order, order_id) is not None:
        thread.order_id = order_id
        await _send_quietly(chat_id, ORDER_GREETING_TEXT)
        if _has_topic(thread):
            await _post_card_quietly(db, thread)
        return
    if param and not is_account_link_param(param):
        # A tampered or unknown order reference is a plain /start.
        param = ""
    if not param:
        await _send_quietly(chat_id, GREETING_TEXT)
        return
    await _link_account(chat_id, sender, param)
    if await _sync_linked_account(db, thread) and _has_topic(thread):
        await _refresh_topic(db, thread)


async def _link_account(chat_id: int, sender: dict, token: str) -> None:
    """The site's one-time account link (``/start <token>``), texts unchanged."""
    status_message_id = None
    try:
        result = await _call("sendMessage", {"chat_id": chat_id, "text": LINK_PENDING_TEXT})
        if isinstance(result, dict):
            status_message_id = result.get("message_id")
    except TelegramApiError as exc:
        if exc.transient:
            # Nothing has happened yet: let Telegram redeliver the update.
            raise
        logger.warning("Help desk: link status message not sent: %s", exc)
    telegram_user = SimpleNamespace(
        id=sender["id"],
        username=sender.get("username"),
        first_name=sender.get("first_name"),
    )
    result_text = await BotAuthService.link_account(token, telegram_user)
    if status_message_id is not None:
        try:
            await _call(
                "editMessageText",
                {"chat_id": chat_id, "message_id": status_message_id, "text": result_text},
            )
            return
        except TelegramApiError as exc:
            logger.warning("Help desk: link result not edited in: %s", exc)
    await _send_quietly(chat_id, result_text)


def _has_topic(thread: HelpdeskThread) -> bool:
    return thread.topic_id is not None and thread.chat_id == settings.TELEGRAM_HELPDESK_CHAT_ID


async def _known_email(db: AsyncSession, thread: HelpdeskThread) -> str | None:
    if thread.user_id is not None:
        email = await db.scalar(select(User.email).where(User.id == thread.user_id))
        if email:
            return email
    return thread.stated_email


async def _topic_name(db: AsyncSession, thread: HelpdeskThread) -> str:
    name = thread.display_name or (
        f"@{thread.telegram_username}" if thread.telegram_username else f"id {thread.telegram_user_id}"
    )
    email = await _known_email(db, thread)
    if email:
        name = f"{name} · {email}"
    return name[:TOPIC_NAME_MAX_LENGTH]


async def _ensure_topic(db: AsyncSession, thread: HelpdeskThread) -> bool:
    """Make sure the customer's topic exists and is open; True when created now."""
    chat_id = settings.TELEGRAM_HELPDESK_CHAT_ID
    if _has_topic(thread):
        if thread.status == "closed":
            try:
                await _call(
                    "reopenForumTopic",
                    {"chat_id": chat_id, "message_thread_id": thread.topic_id},
                )
            except TelegramApiError as exc:
                if exc.transient:
                    raise
                # Already open (reopened by hand): nothing to do.
                logger.info("Help desk: topic not reopened: %s", exc)
            thread.status = "open"
            await _send_quietly(chat_id, REOPENED_TEXT, topic_id=thread.topic_id)
        return False
    result = await _call(
        "createForumTopic",
        {"chat_id": chat_id, "name": await _topic_name(db, thread)},
    )
    if not isinstance(result, dict) or not isinstance(result.get("message_thread_id"), int):
        raise TelegramApiError("Telegram API createForumTopic returned no topic id")
    thread.chat_id = chat_id
    thread.topic_id = result["message_thread_id"]
    thread.status = "open"
    await db.flush()
    await _post_card_quietly(db, thread)
    return True


def _topic_unusable(exc: TelegramApiError) -> str | None:
    """'missing' or 'closed' when a copy failed because of the topic itself."""
    if exc.status_code != 400:
        return None
    description = exc.description.lower()
    if "topic_closed" in description:
        return "closed"
    if any(
        marker in description
        for marker in ("thread not found", "topic_deleted", "topic_id_invalid")
    ):
        return "missing"
    return None


async def _copy_to_topic(db: AsyncSession, thread: HelpdeskThread, message: dict) -> int:
    reply_to = await _group_reply_target(db, thread, message)
    for attempt in range(2):
        payload: dict[str, Any] = {
            "chat_id": thread.chat_id,
            "message_thread_id": thread.topic_id,
            "from_chat_id": message["chat"]["id"],
            "message_id": message["message_id"],
        }
        if reply_to is not None:
            payload["reply_parameters"] = {
                "message_id": reply_to,
                "allow_sending_without_reply": True,
            }
        try:
            result = await _call("copyMessage", payload)
        except TelegramApiError as exc:
            problem = _topic_unusable(exc)
            if attempt == 1 or problem is None:
                raise
            # Operators deleted or closed the topic by hand: recreate or reopen it.
            if problem == "missing":
                thread.topic_id = None
                reply_to = None
            else:
                thread.status = "closed"
            await _ensure_topic(db, thread)
            continue
        if not isinstance(result, dict) or not isinstance(result.get("message_id"), int):
            raise TelegramApiError("Telegram API copyMessage returned no message id")
        return result["message_id"]
    raise AssertionError("unreachable")


async def _group_reply_target(
    db: AsyncSession, thread: HelpdeskThread, message: dict
) -> int | None:
    """The topic copy of the message the customer replied to, if any."""
    reply = message.get("reply_to_message")
    if not isinstance(reply, dict) or not isinstance(reply.get("message_id"), int):
        return None
    return await db.scalar(
        select(HelpdeskMessage.group_message_id)
        .where(
            HelpdeskMessage.thread_id == thread.id,
            HelpdeskMessage.customer_message_id == reply["message_id"],
        )
        .limit(1)
    )


async def _refresh_topic(db: AsyncSession, thread: HelpdeskThread) -> None:
    """New account or email: rename the topic and post a fresh card."""
    try:
        await _call(
            "editForumTopic",
            {
                "chat_id": thread.chat_id,
                "message_thread_id": thread.topic_id,
                "name": await _topic_name(db, thread),
            },
        )
    except TelegramApiError as exc:
        logger.warning("Help desk: topic not renamed: %s", exc)
    await _post_card_quietly(db, thread)


async def _post_card_quietly(db: AsyncSession, thread: HelpdeskThread) -> None:
    await _send_quietly(
        thread.chat_id, await build_customer_card(db, thread), topic_id=thread.topic_id
    )


# --- Operator side -----------------------------------------------------------


async def _handle_operator(db: AsyncSession, message: dict, command: str | None) -> None:
    # The General topic and the alerts topic are never relayed.
    if not message.get("is_topic_message"):
        return
    topic_id = message.get("message_thread_id")
    if not isinstance(topic_id, int) or topic_id == settings.TELEGRAM_HELPDESK_ALERTS_TOPIC_ID:
        return
    thread = await db.scalar(
        select(HelpdeskThread)
        .where(
            HelpdeskThread.chat_id == message["chat"]["id"],
            HelpdeskThread.topic_id == topic_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if thread is None:
        return
    if command is not None:
        if command:
            await _operator_command(db, thread, command)
        return
    content_type = _content_type(message)
    if content_type is None:
        return
    if thread.status == "blocked":
        await _post_to_topic(thread, BLOCKED_NOT_SENT_TEXT)
        return
    payload: dict[str, Any] = {
        "chat_id": thread.telegram_user_id,
        "from_chat_id": thread.chat_id,
        "message_id": message["message_id"],
    }
    reply_to = await _customer_reply_target(db, thread, message)
    if reply_to is not None:
        payload["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
    try:
        result = await _call("copyMessage", payload)
    except TelegramApiError as exc:
        # A relay that fails is reported in the topic, never silently lost.
        if _customer_unreachable(exc):
            notice = UNDELIVERED_UNREACHABLE_TEXT
        else:
            notice = UNDELIVERED_OTHER_TEXT.format(
                reason=exc.description or "Telegram не ответил"
            )
        await _post_to_topic(thread, notice)
        return
    customer_message_id = result.get("message_id") if isinstance(result, dict) else None
    db.add(
        HelpdeskMessage(
            thread_id=thread.id,
            direction=TO_CUSTOMER,
            customer_message_id=customer_message_id,
            group_message_id=message["message_id"],
            content_type=content_type,
            created_at=datetime.utcnow(),
        )
    )
    thread.last_operator_message_at = datetime.utcnow()


def _customer_unreachable(exc: TelegramApiError) -> bool:
    description = exc.description.lower()
    return exc.status_code == 403 or (
        exc.status_code == 400
        and any(marker in description for marker in ("chat not found", "user is deactivated"))
    )


async def _customer_reply_target(
    db: AsyncSession, thread: HelpdeskThread, message: dict
) -> int | None:
    """The customer's copy of the topic message an operator replied to, if any."""
    reply = message.get("reply_to_message")
    if not isinstance(reply, dict) or not isinstance(reply.get("message_id"), int):
        return None
    # In a forum every message "replies" to the topic's first message.
    if reply["message_id"] == thread.topic_id:
        return None
    return await db.scalar(
        select(HelpdeskMessage.customer_message_id)
        .where(
            HelpdeskMessage.thread_id == thread.id,
            HelpdeskMessage.group_message_id == reply["message_id"],
        )
        .limit(1)
    )


async def _operator_command(db: AsyncSession, thread: HelpdeskThread, command: str) -> None:
    if command == "info":
        await _post_to_topic(thread, await build_customer_card(db, thread))
    elif command == "close":
        await _post_to_topic(thread, CLOSED_TEXT)
        try:
            await _call(
                "closeForumTopic",
                {"chat_id": thread.chat_id, "message_thread_id": thread.topic_id},
            )
        except TelegramApiError as exc:
            if exc.transient:
                raise
            logger.info("Help desk: topic not closed: %s", exc)
        if thread.status != "blocked":
            thread.status = "closed"
    elif command == "block":
        thread.status = "blocked"
        await _post_to_topic(thread, BLOCKED_TEXT)
    elif command == "unblock":
        if thread.status == "blocked":
            thread.status = "open"
        await _post_to_topic(thread, UNBLOCKED_TEXT)
    else:
        await _post_to_topic(thread, OPERATOR_HELP_TEXT)


# --- Customer card -----------------------------------------------------------


async def _card_orders(
    db: AsyncSession,
    thread: HelpdeskThread,
    account: User | None,
    email: str | None,
) -> tuple[list[Order], UUID | None]:
    conditions = []
    if account is not None:
        conditions.append(Order.user_id == account.id)
        conditions.append(func.lower(Order.customer_email) == account.email.lower())
    if email:
        conditions.append(func.lower(Order.customer_email) == email.lower())
    orders: list[Order] = []
    if conditions:
        orders = list(
            (
                await db.execute(
                    select(Order)
                    .where(or_(*conditions))
                    .order_by(Order.created_at.desc())
                    .limit(CARD_ORDER_LIMIT)
                )
            )
            .scalars()
            .all()
        )
    context = await db.get(Order, thread.order_id) if thread.order_id else None
    if context is None:
        return orders, None
    others = [order for order in orders if order.id != context.id]
    return [context, *others][:CARD_ORDER_LIMIT], context.id


async def _refunded_order_ids(db: AsyncSession, orders: list[Order]) -> set[UUID]:
    paid_ids = [order.id for order in orders if order.status == "paid"]
    if not paid_ids:
        return set()
    rows = await db.execute(
        select(Purchase.order_id)
        .join(RefundRequest, RefundRequest.purchase_id == Purchase.id)
        .where(Purchase.order_id.in_(paid_ids), RefundRequest.status == "processed")
    )
    return {order_id for order_id in rows.scalars().all() if order_id is not None}


async def build_customer_card(db: AsyncSession, thread: HelpdeskThread) -> str:
    """Plain-text card for operators: who the customer is, orders and access."""
    lines = ["🪪 Карточка клиента", f"Имя: {thread.display_name or '—'}"]
    username = f"@{thread.telegram_username}" if thread.telegram_username else "без username"
    lines.append(f"Telegram: {username}, id {thread.telegram_user_id}")

    account = await db.get(User, thread.user_id) if thread.user_id else None
    stated_email = None
    if account is not None:
        verified = "подтверждён" if account.email_verified_at else "не подтверждён"
        lines.append(f"Аккаунт на сайте: {account.email} (email {verified})")
    elif thread.stated_email:
        stated_email = thread.stated_email
        lines.append(f"Email со слов клиента (не подтверждён): {stated_email}")
        account = await db.scalar(
            select(User).where(func.lower(User.email) == stated_email.lower())
        )
        if account is not None:
            verified = "подтверждён" if account.email_verified_at else "не подтверждён"
            lines.append(f"Аккаунт с этим email есть (email {verified})")
        else:
            lines.append("Аккаунт с этим email не найден")
    else:
        lines.append("Аккаунт не найден")

    orders, context_id = await _card_orders(db, thread, account, stated_email)
    refunded = await _refunded_order_ids(db, orders)
    lines.append("")
    if orders:
        lines.append("Заказы (новые сверху):")
        for order in orders:
            status = "возврат" if order.id in refunded else ORDER_STATUS_LABELS.get(
                order.status, order.status
            )
            marker = "👉 " if order.id == context_id else "• "
            line = (
                f"{marker}{format_msk_datetime(order.created_at)} — {order.course_title} — "
                f"{format_rub(order.amount_kopecks)} — {status} — {order_reference(order.id)}"
            )
            if order.id == context_id:
                line += " (клиент пришёл по ссылке с этим заказом)"
            lines.append(line)
    else:
        lines.append("Заказов нет")

    lines.append("")
    accesses = (
        await AccessService.get_active_course_accesses(db, account.id) if account else []
    )
    if accesses:
        needs_activation = account.role != "admin" and account.email_verified_at is None
        for access in accesses:
            line = f"Доступ: «{access.course.title}» до {format_msk_datetime(access.expires_at)}"
            if needs_activation:
                line += " — откроется после подтверждения email"
            lines.append(line)
    else:
        lines.append("Доступ: доступа нет")
    return "\n".join(lines)
