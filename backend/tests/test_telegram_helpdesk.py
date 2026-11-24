"""Support bot over the Telegram webhook: auth, idempotency, relay both ways.

The Bot API is answered at the httpx layer of outbox_service, the only place
that talks to Telegram.
"""

import hashlib
import itertools
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.outbox_service as outbox_service
import app.services.telegram_helpdesk_service as helpdesk
from app.core.config import Settings, settings
from app.core.security import get_password_hash
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.order import Order
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.telegram_helpdesk import HelpdeskMessage, HelpdeskThread, TelegramUpdate
from app.models.telegram_link import TelegramLinkToken
from app.models.user import User
from app.services.support_links import (
    is_account_link_param,
    issue_order_start_param,
    verify_order_start_param,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "telegram_webhook.py"
BOT_ID = 7000001
BOT_TOKEN = f"{BOT_ID}:helpdesk-test-token-AAAAAAAAAAAAAAAAAAAA"
SECRET = "webhook-secret-for-tests-0123456789abcdef"
GROUP_ID = -1001234567890
ALERTS_TOPIC = 77
CUSTOMER_ID = 424242
OPERATOR_ID = 9001
WEBHOOK = "/api/telegram/webhook"

_update_ids = itertools.count(1)
_message_ids = itertools.count(100)


class FakeTelegram:
    """Records Bot API calls and answers them like Telegram would."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.responders: dict[str, object] = {}
        self._ids = itertools.count(5000)
        self._topics = itertools.count(300)

    def handler(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        payload = json.loads(request.content or b"{}")
        self.calls.append((method, payload))
        responder = self.responders.get(method)
        if responder is not None:
            response = responder(payload)
            if response is not None:
                return response
        if method == "createForumTopic":
            return _ok({"message_thread_id": next(self._topics), "name": payload["name"]})
        if method in {"sendMessage", "copyMessage"}:
            return _ok({"message_id": next(self._ids)})
        return _ok(True)

    def of(self, method: str) -> list[dict]:
        return [payload for name, payload in self.calls if name == method]

    def to_chat(self, chat_id: int) -> list[dict]:
        return [
            payload for name, payload in self.calls
            if name in {"sendMessage", "copyMessage", "editMessageText"}
            and payload.get("chat_id") == chat_id
        ]

    def texts_to(self, chat_id: int) -> list[str]:
        return [payload["text"] for payload in self.to_chat(chat_id) if "text" in payload]


def _ok(result) -> httpx.Response:
    return httpx.Response(200, json={"ok": True, "result": result})


def _error(status: int, description: str) -> httpx.Response:
    return httpx.Response(
        status, json={"ok": False, "error_code": status, "description": description}
    )


@pytest.fixture
def telegram(monkeypatch: pytest.MonkeyPatch) -> FakeTelegram:
    fake = FakeTelegram()
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        outbox_service,
        "httpx",
        SimpleNamespace(
            AsyncClient=lambda **kwargs: real_client(
                transport=httpx.MockTransport(fake.handler), **kwargs
            ),
            HTTPError=httpx.HTTPError,
            Response=httpx.Response,
        ),
    )
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "lucynails_test_bot")
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_CHAT_ID", GROUP_ID)
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_ALERTS_TOPIC_ID", ALERTS_TOPIC)
    return fake


def private_update(text: str | None = "Здравствуйте, не пришло письмо", *, user_id: int = CUSTOMER_ID,
                   update_id: int | None = None, **extra) -> dict:
    message = {
        "message_id": next(_message_ids),
        "date": 1_790_000_000,
        "chat": {"id": user_id, "type": "private", "first_name": "Анна"},
        "from": {"id": user_id, "is_bot": False, "first_name": "Анна", "last_name": "Петрова",
                 "username": "anna_nails"},
        **extra,
    }
    if text is not None:
        message["text"] = text
    return {"update_id": update_id or next(_update_ids), "message": message}


def group_update(topic_id: int | None, text: str | None = "Добрый день! Проверяем заказ.", *,
                 chat_id: int = GROUP_ID, from_id: int = OPERATOR_ID, is_bot: bool = False,
                 **extra) -> dict:
    message = {
        "message_id": next(_message_ids),
        "date": 1_790_000_000,
        "chat": {"id": chat_id, "type": "supergroup", "title": "Поддержка", "is_forum": True},
        "from": {"id": from_id, "is_bot": is_bot, "first_name": "Оператор"},
        **extra,
    }
    if topic_id is not None:
        message["message_thread_id"] = topic_id
        message["is_topic_message"] = True
    if text is not None:
        message["text"] = text
    return {"update_id": next(_update_ids), "message": message}


async def deliver(client: AsyncClient, update, *, secret: str = SECRET) -> httpx.Response:
    return await client.post(
        WEBHOOK, json=update, headers={"X-Telegram-Bot-Api-Secret-Token": secret}
    )


async def _thread(db: AsyncSession, telegram_user_id: int = CUSTOMER_ID) -> HelpdeskThread | None:
    db.expire_all()
    return await db.scalar(
        select(HelpdeskThread).where(HelpdeskThread.telegram_user_id == telegram_user_id)
    )


async def _open_topic(client: AsyncClient, db: AsyncSession, telegram: FakeTelegram) -> HelpdeskThread:
    response = await deliver(client, private_update())
    assert response.status_code == 200, response.text
    thread = await _thread(db)
    assert thread is not None and thread.topic_id is not None
    return thread


async def _course(db: AsyncSession, title: str = "Маникюр с нуля") -> Course:
    course = Course(title=title, price_self=5900, price_support=9900, is_published=True)
    db.add(course)
    await db.flush()
    return course


async def _order(db: AsyncSession, course: Course, email: str, *, status: str = "pending",
                 user_id=None, created_at: datetime | None = None) -> Order:
    order = Order(
        user_id=user_id,
        course_id=course.id,
        course_title=course.title,
        tariff="self",
        customer_email=email,
        amount_kopecks=590000,
        currency="RUB",
        access_days=30,
        status=status,
        status_token_hash="0" * 64,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(order)
    await db.flush()
    return order


# --- Webhook authentication and transport ------------------------------------


@pytest.mark.asyncio
async def test_webhook_is_off_without_a_secret(client: AsyncClient, telegram: FakeTelegram,
                                              monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")

    response = await deliver(client, private_update(), secret="")

    assert response.status_code == 404
    assert telegram.calls == []


@pytest.mark.asyncio
async def test_webhook_rejects_missing_or_wrong_secret_before_reading_the_body(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    missing = await client.post(WEBHOOK, content=b"not json at all")
    wrong = await client.post(
        WEBHOOK, content=b"not json at all",
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET[:-1] + "x"},
    )

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert await db.scalar(select(func.count()).select_from(TelegramUpdate)) == 0
    assert telegram.calls == []


@pytest.mark.asyncio
async def test_webhook_accepts_the_right_secret(client: AsyncClient, db: AsyncSession,
                                                telegram: FakeTelegram):
    update = private_update("/start")

    response = await deliver(client, update)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert await db.get(TelegramUpdate, update["update_id"]) is not None


@pytest.mark.asyncio
async def test_webhook_rejects_an_oversized_body(client: AsyncClient, telegram: FakeTelegram):
    body = json.dumps({"update_id": 1, "padding": "x" * (256 * 1024)}).encode()

    response = await client.post(
        WEBHOOK, content=body,
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET, "content-type": "application/json"},
    )

    assert response.status_code == 413
    assert telegram.calls == []


@pytest.mark.asyncio
async def test_webhook_ignores_malformed_and_unsupported_updates(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    headers = {"X-Telegram-Bot-Api-Secret-Token": SECRET}
    for body in (b"{broken", b"[]", b'{"update_id": "12"}', b'{"no_update_id": true}'):
        response = await client.post(WEBHOOK, content=body, headers=headers)
        assert response.status_code == 200, body
    edited = {"update_id": next(_update_ids), "edited_message": {"message_id": 1}}
    weird = {"update_id": next(_update_ids), "message": {"chat": "nope"}}
    assert (await deliver(client, edited)).status_code == 200
    assert (await deliver(client, weird)).status_code == 200
    assert telegram.calls == []


@pytest.mark.asyncio
async def test_webhook_works_with_stray_cookies_and_no_csrf_header(
    client: AsyncClient, telegram: FakeTelegram
):
    client.cookies.set("access_token", "stale-session-cookie")
    try:
        wrong = await client.post(WEBHOOK, json=private_update(),
                                  headers={"X-Telegram-Bot-Api-Secret-Token": "nope"})
        right = await deliver(client, private_update("/start"))
    finally:
        client.cookies.clear()

    assert wrong.status_code == 403
    assert wrong.json()["detail"] == "Forbidden"
    assert right.status_code == 200


@pytest.mark.asyncio
async def test_csrf_still_guards_other_paths_with_cookies(client: AsyncClient):
    client.cookies.set("access_token", "stale-session-cookie")
    try:
        response = await client.post("/api/telegram/link")
    finally:
        client.cookies.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing or invalid"


@pytest.mark.asyncio
async def test_an_update_delivered_twice_is_handled_once(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    update = private_update("Вопрос по оплате")

    first = await deliver(client, update)
    second = await deliver(client, update)

    assert first.status_code == second.status_code == 200
    assert len(telegram.of("copyMessage")) == 1
    assert len(telegram.of("createForumTopic")) == 1
    assert await db.scalar(select(func.count()).select_from(HelpdeskMessage)) == 1


@pytest.mark.asyncio
async def test_a_temporary_telegram_failure_asks_for_redelivery(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    failures = iter([_error(502, "Bad Gateway")])
    telegram.responders["copyMessage"] = lambda _payload: next(failures, None)
    update = private_update("Не открывается урок")

    failed = await deliver(client, update)
    assert failed.status_code == 503
    assert await db.get(TelegramUpdate, update["update_id"]) is None

    retried = await deliver(client, update)
    assert retried.status_code == 200
    db.expire_all()
    assert await db.scalar(select(func.count()).select_from(HelpdeskMessage)) == 1


@pytest.mark.asyncio
async def test_an_update_that_keeps_failing_is_skipped_not_redelivered_forever(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram, monkeypatch: pytest.MonkeyPatch
):
    async def broken(*_args, **_kwargs):
        raise ValueError("bug")

    monkeypatch.setattr(helpdesk, "_handle_customer", broken)
    update = private_update("Привет")

    response = await deliver(client, update)

    assert response.status_code == 200
    assert await db.get(TelegramUpdate, update["update_id"]) is not None


# --- /start ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_without_argument_greets_and_asks_for_the_email(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    assert (await deliver(client, private_update("/start"))).status_code == 200

    assert telegram.texts_to(CUSTOMER_ID) == [helpdesk.GREETING_TEXT]
    assert "email" in helpdesk.GREETING_TEXT
    assert telegram.of("createForumTopic") == []


@pytest.mark.asyncio
async def test_start_with_a_signed_order_reference_attaches_the_order(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    course = await _course(db)
    order = await _order(db, course, "buyer@example.com")
    await db.commit()
    order_id = order.id
    param = issue_order_start_param(order_id)
    assert len(param) <= 64

    assert (await deliver(client, private_update(f"/start {param}"))).status_code == 200

    thread = await _thread(db)
    assert thread.order_id == order_id
    assert telegram.texts_to(CUSTOMER_ID) == [helpdesk.ORDER_GREETING_TEXT]
    # The customer is told nothing about the order itself.
    assert "buyer@example.com" not in helpdesk.ORDER_GREETING_TEXT

    await deliver(client, private_update("Списались деньги, а доступа нет"))
    card = telegram.of("sendMessage")[1]["text"]
    assert card.startswith("🪪 Карточка клиента")
    assert f"order|{order_id}" in card
    assert "клиент пришёл по ссылке с этим заказом" in card


@pytest.mark.asyncio
async def test_start_with_a_tampered_order_reference_is_a_plain_start(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    course = await _course(db)
    order = await _order(db, course, "buyer@example.com")
    await db.commit()
    param = issue_order_start_param(order.id)
    tampered = param[:-1] + ("A" if param[-1] != "A" else "B")
    truncated = param[:30]

    await deliver(client, private_update(f"/start {tampered}"))
    await deliver(client, private_update(f"/start {truncated}"))

    thread = await _thread(db)
    assert thread.order_id is None
    assert telegram.texts_to(CUSTOMER_ID) == [helpdesk.GREETING_TEXT, helpdesk.GREETING_TEXT]


@pytest.mark.asyncio
async def test_start_with_an_account_token_links_the_account_and_the_thread(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    user = User(email="linked@example.com", email_verified_at=datetime.utcnow(),
                password_hash=get_password_hash("linked-password-123"), role="student")
    db.add(user)
    await db.flush()
    token = secrets.token_urlsafe(32)
    db.add(TelegramLinkToken(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    ))
    await db.commit()
    user_id = user.id

    assert (await deliver(client, private_update(f"/start {token}"))).status_code == 200

    assert telegram.of("sendMessage")[0]["text"] == "⏳ Проверяю данные..."
    edited = telegram.of("editMessageText")
    assert len(edited) == 1
    assert edited[0]["text"].startswith("✅ Аккаунт успешно привязан.")
    thread = await _thread(db)
    assert thread.user_id == user_id
    assert (await db.get(User, user_id)).telegram_id == CUSTOMER_ID


@pytest.mark.asyncio
async def test_start_with_an_unknown_account_token_keeps_the_old_answer(
    client: AsyncClient, telegram: FakeTelegram
):
    await deliver(client, private_update(f"/start {secrets.token_urlsafe(32)}"))

    assert telegram.of("editMessageText")[0]["text"] == (
        "Ссылка некорректна. Создайте новую в личном кабинете."
    )


# --- Customer messages -------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_messages_create_one_topic_and_are_copied(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    first = private_update("Здравствуйте! Не могу войти")
    photo = private_update(None, photo=[{"file_id": "p", "file_unique_id": "u", "width": 1, "height": 1}])

    assert (await deliver(client, first)).status_code == 200
    assert (await deliver(client, photo)).status_code == 200

    topics = telegram.of("createForumTopic")
    assert len(topics) == 1
    assert topics[0]["chat_id"] == GROUP_ID
    assert topics[0]["name"] == "Анна Петрова"
    thread = await _thread(db)
    copies = telegram.of("copyMessage")
    assert [c["from_chat_id"] for c in copies] == [CUSTOMER_ID, CUSTOMER_ID]
    assert [c["message_id"] for c in copies] == [first["message"]["message_id"], photo["message"]["message_id"]]
    assert all(c["chat_id"] == GROUP_ID and c["message_thread_id"] == thread.topic_id for c in copies)
    cards = [p for p in telegram.of("sendMessage") if p.get("message_thread_id") == thread.topic_id]
    assert len(cards) == 1 and cards[0]["text"].startswith("🪪 Карточка клиента")
    # Acknowledged once, not for every message.
    assert telegram.texts_to(CUSTOMER_ID) == [helpdesk.ACK_ASK_EMAIL_TEXT]
    kinds = (await db.execute(select(HelpdeskMessage.content_type))).scalars().all()
    assert sorted(kinds) == ["photo", "text"]


@pytest.mark.asyncio
async def test_customer_is_acknowledged_again_after_a_few_hours(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    thread = await _open_topic(client, db, telegram)
    thread.last_ack_at = datetime.utcnow() - helpdesk.ACK_INTERVAL - timedelta(minutes=1)
    await db.commit()

    await deliver(client, private_update("Ещё вопрос"))

    assert telegram.texts_to(CUSTOMER_ID) == [helpdesk.ACK_ASK_EMAIL_TEXT, helpdesk.ACK_ASK_EMAIL_TEXT]


@pytest.mark.asyncio
async def test_a_typed_email_reveals_nothing_to_the_customer(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    course = await _course(db, "Секретный курс")
    owner = User(email="victim@example.com", email_verified_at=datetime.utcnow(),
                 password_hash=get_password_hash("victim-password-123"), role="student")
    db.add(owner)
    await db.flush()
    await _order(db, course, "victim@example.com", status="paid", user_id=owner.id)
    await db.commit()
    thread = await _open_topic(client, db, telegram)

    await deliver(client, private_update("Victim@Example.com"))
    await deliver(client, private_update("nobody@example.com", user_id=CUSTOMER_ID + 1))

    for chat_id in (CUSTOMER_ID, CUSTOMER_ID + 1):
        for text in telegram.texts_to(chat_id):
            assert "Секретный" not in text and "5 900" not in text and "order|" not in text
            assert "victim" not in text.lower() and "не найден" not in text
    assert telegram.texts_to(CUSTOMER_ID)[-1] == helpdesk.EMAIL_ACK_TEXT
    assert telegram.texts_to(CUSTOMER_ID + 1)[-1] == helpdesk.EMAIL_ACK_TEXT
    thread = await _thread(db)
    assert thread.stated_email == "victim@example.com"
    # The operators get the refreshed card and a renamed topic.
    renamed = telegram.of("editForumTopic")
    assert renamed[0]["name"] == "Анна Петрова · victim@example.com"
    card = [p["text"] for p in telegram.of("sendMessage")
            if p.get("message_thread_id") == thread.topic_id][-1]
    assert "Email со слов клиента (не подтверждён): victim@example.com" in card
    assert "Секретный курс" in card and "оплачен" in card


@pytest.mark.asyncio
async def test_flood_limit_drops_extra_messages_with_one_notice(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    for index in range(helpdesk.FLOOD_LIMIT + 3):
        response = await deliver(client, private_update(f"Сообщение {index}"))
        assert response.status_code == 200

    assert len(telegram.of("copyMessage")) == helpdesk.FLOOD_LIMIT
    assert telegram.texts_to(CUSTOMER_ID).count(helpdesk.FLOOD_TEXT) == 1


@pytest.mark.asyncio
async def test_customer_message_without_helpdesk_points_to_email(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_CHAT_ID", None)

    await deliver(client, private_update("/start"))
    await deliver(client, private_update("Помогите"))

    assert telegram.texts_to(CUSTOMER_ID) == [helpdesk.HELPDESK_OFF_TEXT] * 2
    assert helpdesk.SUPPORT_EMAIL in helpdesk.HELPDESK_OFF_TEXT
    assert await _thread(db) is None
    assert telegram.of("copyMessage") == []


@pytest.mark.asyncio
async def test_a_relay_the_group_refuses_is_reported_to_the_customer(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    telegram.responders["createForumTopic"] = lambda _p: _error(400, "Bad Request: not enough rights")

    response = await deliver(client, private_update("Вопрос"))

    assert response.status_code == 200
    assert telegram.texts_to(CUSTOMER_ID) == [helpdesk.RELAY_FAILED_TEXT]


@pytest.mark.asyncio
async def test_a_deleted_topic_is_recreated(client: AsyncClient, db: AsyncSession, telegram: FakeTelegram):
    thread = await _open_topic(client, db, telegram)
    old_topic = thread.topic_id
    telegram.responders["copyMessage"] = lambda payload: (
        _error(400, "Bad Request: message thread not found")
        if payload.get("message_thread_id") == old_topic else None
    )

    assert (await deliver(client, private_update("Снова я"))).status_code == 200

    thread = await _thread(db)
    assert thread.topic_id != old_topic
    assert len(telegram.of("createForumTopic")) == 2


# --- Operators ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_operator_message_in_the_topic_reaches_the_customer(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    customer_message = private_update("Где письмо?")
    await deliver(client, customer_message)
    thread = await _thread(db)
    group_copy = await db.scalar(select(HelpdeskMessage.group_message_id))
    reply = group_update(
        thread.topic_id,
        "Отправили повторно, проверьте «Спам».",
        reply_to_message={"message_id": group_copy},
    )

    assert (await deliver(client, reply)).status_code == 200

    relayed = telegram.of("copyMessage")[-1]
    assert relayed["chat_id"] == CUSTOMER_ID
    assert relayed["from_chat_id"] == GROUP_ID
    assert relayed["message_id"] == reply["message"]["message_id"]
    assert relayed["reply_parameters"]["message_id"] == customer_message["message"]["message_id"]
    thread = await _thread(db)
    assert thread.last_operator_message_at is not None


@pytest.mark.asyncio
async def test_operator_message_the_customer_cannot_receive_is_reported_in_the_topic(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    thread = await _open_topic(client, db, telegram)
    telegram.responders["copyMessage"] = lambda payload: (
        _error(403, "Forbidden: bot was blocked by the user")
        if payload["chat_id"] == CUSTOMER_ID else None
    )

    assert (await deliver(client, group_update(thread.topic_id))).status_code == 200

    notice = telegram.of("sendMessage")[-1]
    assert notice["chat_id"] == GROUP_ID and notice["message_thread_id"] == thread.topic_id
    assert notice["text"] == helpdesk.UNDELIVERED_UNREACHABLE_TEXT


@pytest.mark.asyncio
async def test_messages_outside_customer_topics_are_never_relayed(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    await _open_topic(client, db, telegram)
    before = len(telegram.calls)

    await deliver(client, group_update(None, "Сообщение в General"))
    await deliver(client, group_update(ALERTS_TOPIC, "Обсуждаем оплату"))
    await deliver(client, group_update(999, "Тема без клиента"))
    await deliver(client, group_update((await _thread(db)).topic_id, "от бота", from_id=BOT_ID, is_bot=True))
    await deliver(client, group_update((await _thread(db)).topic_id, "чужой бот", from_id=5555, is_bot=True))

    assert telegram.calls[before:] == []


@pytest.mark.asyncio
async def test_anonymous_operator_messages_are_relayed(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    thread = await _open_topic(client, db, telegram)

    await deliver(client, group_update(
        thread.topic_id, "Ответ анонимного админа", from_id=1087968824, is_bot=True,
        sender_chat={"id": GROUP_ID, "type": "supergroup", "title": "Поддержка"},
    ))

    assert telegram.of("copyMessage")[-1]["chat_id"] == CUSTOMER_ID


@pytest.mark.asyncio
async def test_messages_from_another_group_are_ignored_but_chatid_answers(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    thread = await _open_topic(client, db, telegram)
    before = len(telegram.calls)

    await deliver(client, group_update(thread.topic_id, "чужая группа", chat_id=-100999))
    assert telegram.calls[before:] == []

    await deliver(client, group_update(None, "/chatid", chat_id=-100999))
    await deliver(client, group_update(ALERTS_TOPIC, "/chatid@lucynails_test_bot"))
    answers = telegram.of("sendMessage")[-2:]
    assert answers[0] == {"chat_id": -100999, "text": "ID чата: -100999"}
    assert answers[1] == {
        "chat_id": GROUP_ID,
        "text": f"ID чата: {GROUP_ID}\nID темы: {ALERTS_TOPIC}",
        "message_thread_id": ALERTS_TOPIC,
    }


@pytest.mark.asyncio
async def test_close_then_a_new_customer_message_reopens(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    thread = await _open_topic(client, db, telegram)

    await deliver(client, group_update(thread.topic_id, "/close"))
    assert telegram.of("closeForumTopic") == [{"chat_id": GROUP_ID, "message_thread_id": thread.topic_id}]
    assert (await _thread(db)).status == "closed"
    assert telegram.of("copyMessage")[-1]["chat_id"] == GROUP_ID  # /close is not relayed

    await deliver(client, private_update("Ещё один вопрос"))

    assert telegram.of("reopenForumTopic") == [{"chat_id": GROUP_ID, "message_thread_id": thread.topic_id}]
    assert (await _thread(db)).status == "open"
    assert telegram.of("copyMessage")[-1]["message_thread_id"] == thread.topic_id
    assert len(telegram.of("createForumTopic")) == 1


@pytest.mark.asyncio
async def test_block_silences_the_customer_until_unblock(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    thread = await _open_topic(client, db, telegram)

    await deliver(client, group_update(thread.topic_id, "/block"))
    assert (await _thread(db)).status == "blocked"
    before = len(telegram.calls)
    await deliver(client, private_update("спам"))
    await deliver(client, private_update("/start"))
    assert telegram.calls[before:] == []

    await deliver(client, group_update(thread.topic_id, "Ответ заблокированному"))
    assert telegram.of("sendMessage")[-1]["text"] == helpdesk.BLOCKED_NOT_SENT_TEXT

    await deliver(client, group_update(thread.topic_id, "/unblock"))
    await deliver(client, private_update("Я снова тут"))
    assert (await _thread(db)).status == "open"
    assert telegram.of("copyMessage")[-1]["from_chat_id"] == CUSTOMER_ID


@pytest.mark.asyncio
async def test_info_reposts_the_card_and_unknown_commands_get_help(
    client: AsyncClient, db: AsyncSession, telegram: FakeTelegram
):
    thread = await _open_topic(client, db, telegram)

    await deliver(client, group_update(thread.topic_id, "/info"))
    await deliver(client, group_update(thread.topic_id, "/what"))

    texts = [p["text"] for p in telegram.of("sendMessage")[-2:]]
    assert texts[0].startswith("🪪 Карточка клиента")
    assert texts[1] == helpdesk.OPERATOR_HELP_TEXT
    assert all(c["chat_id"] != CUSTOMER_ID for c in telegram.of("copyMessage"))


# --- Customer card -----------------------------------------------------------


@pytest.mark.asyncio
async def test_card_for_a_linked_account_lists_orders_and_access(db: AsyncSession):
    course = await _course(db, "Курс маникюра")
    user = User(email="Student@Example.com", email_verified_at=datetime.utcnow(),
                password_hash=get_password_hash("student-password-1"), role="student",
                telegram_id=CUSTOMER_ID)
    db.add(user)
    await db.flush()
    paid = await _order(db, course, "student@example.com", status="paid", user_id=user.id,
                        created_at=datetime(2026, 11, 20, 9, 0))
    refunded = await _order(db, course, "student@example.com", status="paid", user_id=user.id,
                            created_at=datetime(2026, 11, 1, 9, 0))
    await _order(db, course, "student@example.com", created_at=datetime(2026, 11, 21, 9, 0))
    for index in range(4):
        await _order(db, course, "student@example.com", created_at=datetime(2026, 10, 1 + index))
    purchase = Purchase(user_id=user.id, course_id=course.id, order_id=refunded.id, tariff="self",
                        amount_kopecks=590000, payment_id="refunded-payment", payment_status="success",
                        paid_at=datetime(2026, 11, 1), expires_at=datetime(2026, 12, 1))
    db.add(purchase)
    await db.flush()
    db.add(RefundRequest(purchase_id=purchase.id, amount_kopecks=590000, reason="test",
                         status="processed", created_by_id=user.id))
    db.add(Entitlement(user_id=user.id, course_id=course.id, source="manual", tariff="self",
                       status="active", starts_at=datetime.utcnow() - timedelta(days=1),
                       expires_at=datetime(2030, 1, 15, 12, 0)))
    thread = HelpdeskThread(telegram_user_id=CUSTOMER_ID, display_name="Анна",
                            telegram_username="anna_nails", user_id=user.id, status="open")
    db.add(thread)
    await db.flush()

    card = await helpdesk.build_customer_card(db, thread)

    assert "Telegram: @anna_nails, id 424242" in card
    assert "Аккаунт на сайте: Student@Example.com (email подтверждён)" in card
    order_lines = [line for line in card.splitlines() if line.startswith("• ")]
    assert len(order_lines) == helpdesk.CARD_ORDER_LIMIT
    assert order_lines[0].startswith("• 21.11.2026 12:00 (МСК) — Курс маникюра — 5 900 ₽ — не оплачен")
    assert order_lines[1].startswith("• 20.11.2026 12:00 (МСК)") and "— оплачен —" in order_lines[1]
    assert "— возврат —" in order_lines[2] and str(refunded.id) in order_lines[2]
    assert str(paid.id) in order_lines[1]
    assert "Доступ: «Курс маникюра» до 15.01.2030 15:00 (МСК)" in card


@pytest.mark.asyncio
async def test_card_for_a_stated_email_marks_it_unconfirmed(db: AsyncSession):
    course = await _course(db)
    await _order(db, course, "guest@example.com")
    thread = HelpdeskThread(telegram_user_id=CUSTOMER_ID, display_name="Гость",
                            stated_email="guest@example.com", status="open")
    db.add(thread)
    await db.flush()

    card = await helpdesk.build_customer_card(db, thread)

    assert "Telegram: без username" in card
    assert "Email со слов клиента (не подтверждён): guest@example.com" in card
    assert "Аккаунт с этим email не найден" in card
    assert "не оплачен" in card
    assert "Доступ: доступа нет" in card


@pytest.mark.asyncio
async def test_card_for_an_unknown_customer(db: AsyncSession):
    thread = HelpdeskThread(telegram_user_id=CUSTOMER_ID, status="open")
    db.add(thread)
    await db.flush()

    card = await helpdesk.build_customer_card(db, thread)

    assert "Аккаунт не найден" in card
    assert "Заказов нет" in card
    assert "Доступ: доступа нет" in card


@pytest.mark.asyncio
async def test_processed_updates_are_pruned_after_a_week(db: AsyncSession):
    now = datetime.utcnow()
    db.add_all([
        TelegramUpdate(update_id=1, received_at=now - timedelta(days=8)),
        TelegramUpdate(update_id=2, received_at=now - timedelta(days=1)),
    ])
    await db.flush()

    await helpdesk.prune_processed_updates(db, now=now)

    remaining = (await db.execute(select(TelegramUpdate.update_id))).scalars().all()
    assert remaining == [2]


# --- Support links, production settings, webhook script ---------------------



def test_order_start_param_round_trip_and_tampering():
    order_id = uuid4()
    param = issue_order_start_param(order_id)

    assert param.startswith("o_") and len(param) == 45
    assert all(char.isalnum() or char in "_-" for char in param)
    assert verify_order_start_param(param) == order_id
    flipped = param[:10] + ("A" if param[10] != "A" else "B") + param[11:]
    assert verify_order_start_param(flipped) is None
    assert verify_order_start_param(param[:-1]) is None
    assert verify_order_start_param("o_" + "!" * 43) is None
    assert verify_order_start_param(param.replace("o_", "x_", 1)) is None
    # A 43-character account token that starts with "o_" still links an account.
    assert is_account_link_param("o_" + "a" * 41)
    assert not is_account_link_param(param)
    assert not is_account_link_param(param[:20])


def test_order_start_param_depends_on_the_application_secret(monkeypatch: pytest.MonkeyPatch):
    order_id = uuid4()
    param = issue_order_start_param(order_id)
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "another-secret-for-this-test-only-123")

    assert verify_order_start_param(param) is None


def _production(**overrides):
    kwargs = dict(
        _env_file=None,
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="production-secret-that-is-32-chars-min",
        MFA_ENCRYPTION_KEY="distinct-mfa-encryption-key-32-chars-min",
        KINESCOPE_API_KEY="kinescope-key",
        KINESCOPE_JWT_PRIVATE_KEY_PEM="dummy-pem",
        KINESCOPE_JWK_KID="kid-test",
        KINESCOPE_DRM_BASIC_USER="drm-user",
        KINESCOPE_DRM_BASIC_PASS="drm-pass",
        PRODAMUS_URL="https://shop.payform.ru/",
        PRODAMUS_SECRET_KEY="prodamus-secret",
        PRODAMUS_SHOP_ID="shop-id",
        FRONTEND_URL="https://lucysmirnova.ru",
        BACKEND_URL="https://api.lucysmirnova.ru",
        COOKIE_DOMAIN="lucysmirnova.ru",
        TRUSTED_HOSTS="api.lucysmirnova.ru",
        REDIS_URL="redis://shared-redis.internal:6379/0",
        TELEGRAM_BOT_TOKEN="telegram-token",
        TELEGRAM_BOT_USERNAME="lucy_nails_bot",
        TELEGRAM_OWNER_CHAT_ID=123456789,
        RESEND_API_KEY="re_default_key",
    )
    kwargs.update(overrides)
    return Settings(**kwargs)


def test_production_requires_a_webhook_secret_for_the_helpdesk():
    good_secret = "A" * 32
    assert _production().TELEGRAM_HELPDESK_CHAT_ID is None
    assert _production(TELEGRAM_HELPDESK_CHAT_ID=GROUP_ID, TELEGRAM_WEBHOOK_SECRET=good_secret,
                       TELEGRAM_HELPDESK_ALERTS_TOPIC_ID=ALERTS_TOPIC)
    for overrides, message in (
        ({"TELEGRAM_HELPDESK_CHAT_ID": GROUP_ID}, "TELEGRAM_WEBHOOK_SECRET"),
        ({"TELEGRAM_HELPDESK_CHAT_ID": GROUP_ID, "TELEGRAM_WEBHOOK_SECRET": "A" * 31},
         "TELEGRAM_WEBHOOK_SECRET"),
        ({"TELEGRAM_HELPDESK_CHAT_ID": GROUP_ID, "TELEGRAM_WEBHOOK_SECRET": "A" * 31 + "!"},
         "TELEGRAM_WEBHOOK_SECRET"),
        ({"TELEGRAM_HELPDESK_CHAT_ID": 12345, "TELEGRAM_WEBHOOK_SECRET": good_secret},
         "negative supergroup id"),
        ({"TELEGRAM_WEBHOOK_SECRET": "short"}, "TELEGRAM_WEBHOOK_SECRET"),
        ({"TELEGRAM_HELPDESK_ALERTS_TOPIC_ID": ALERTS_TOPIC}, "requires TELEGRAM_HELPDESK_CHAT_ID"),
    ):
        with pytest.raises(ValidationError) as error:
            _production(**overrides)
        assert message in str(error.value)


# Runs the script as a process with the Bot API answered in memory; the
# requests it made are written to the file named by argv[1].
SCRIPT_RUNNER = """
import json, runpy, sys
import httpx

calls = []
real_client = httpx.AsyncClient

def handler(request):
    calls.append([request.url.path.rsplit("/", 1)[-1], json.loads(request.content or b"{}")])
    return httpx.Response(200, json={"ok": True, "result": {
        "url": "https://api.example.test/api/telegram/webhook",
        "pending_update_count": 0,
        "last_error_message": "Wrong response from the webhook: 503 Service Unavailable",
    }})

httpx.AsyncClient = lambda **kwargs: real_client(
    **{**kwargs, "transport": httpx.MockTransport(handler)}
)
out_path, script, *args = sys.argv[1:]
sys.argv = [script, *args]
code = 0
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    code = exc.code
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump({"code": code, "calls": calls}, handle)
"""


def _run_script(tmp_path: Path, *args: str, token: str, secret: str) -> tuple[dict, str]:
    out_path = tmp_path / f"calls-{args[0]}.json"
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT_RUNNER, str(out_path), str(SCRIPT), *args],
        env={
            **os.environ,
            "PYTHONPATH": str(SCRIPT.parents[1]),
            "PYTHONIOENCODING": "utf-8",
            "TELEGRAM_BOT_TOKEN": token,
            "TELEGRAM_WEBHOOK_SECRET": secret,
            "BACKEND_URL": "https://api.example.test/",
        },
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert out_path.exists(), result.stderr
    return json.loads(out_path.read_text(encoding="utf-8")), result.stdout + result.stderr


def test_webhook_script_sets_info_and_deletes_without_printing_secrets(tmp_path: Path):
    token = "7000001:script-test-token-BBBBBBBBBBBBBBBBBBBB"
    secret = "script-webhook-secret-0123456789abcdef"

    set_run, set_output = _run_script(tmp_path, "set", token=token, secret=secret)
    info_run, info_output = _run_script(tmp_path, "info", token=token, secret=secret)
    delete_run, delete_output = _run_script(tmp_path, "delete", token=token, secret=secret)

    assert [run["code"] for run in (set_run, info_run, delete_run)] == [0, 0, 0]
    assert set_run["calls"] == [["setWebhook", {
        "url": "https://api.example.test/api/telegram/webhook",
        "secret_token": secret,
        "allowed_updates": ["message"],
        "drop_pending_updates": False,
        "max_connections": 1,
    }]]
    assert info_run["calls"] == [["getWebhookInfo", {}]]
    assert delete_run["calls"] == [["deleteWebhook", {"drop_pending_updates": False}]]
    printed = set_output + info_output + delete_output
    assert secret not in printed and "script-test-token" not in printed
    assert "https://api.example.test/api/telegram/webhook" in set_output
    assert "503 Service Unavailable" in info_output


def test_webhook_script_refuses_a_weak_secret(tmp_path: Path):
    run, output = _run_script(
        tmp_path, "set", token="7000001:script-test-token-CCCCCCCCCCCCCCCCCCCC", secret="short-secret"
    )

    assert run == {"code": 2, "calls": []}
    assert "short-secret" not in output and "script-test-token" not in output
