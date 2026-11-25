"""Order and payment alerts for the owner: routing, new kinds, dedupe, emails."""

import json
import logging
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from conftest import TestingSessionLocal
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.outbox_service as outbox_service
import app.services.owner_alerts as owner_alerts_module
from app.core.config import Settings, settings
from app.core.security import create_account_activation_token, get_password_hash
from app.models.course import Course
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.purchase import Purchase
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.lifecycle_service import LifecycleService
from app.services.owner_alerts import (
    schedule_abandoned_order_alerts,
    schedule_missing_order_created_alerts,
)
from app.services.prodamus_service import _make_signature

OWNER_CHAT = 555000111
GROUP_ID = -1001234567890
ALERTS_TOPIC = 77

# A database-side failure of exactly one kind of write: owner alert inserts.
BREAK_OWNER_ALERT_INSERTS = (
    """
    CREATE OR REPLACE FUNCTION test_break_owner_alerts() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.kind LIKE 'owner_%' THEN
            RAISE EXCEPTION 'outbox_messages is unavailable';
        END IF;
        RETURN NEW;
    END $$
    """,
    "CREATE TRIGGER test_break_owner_alerts BEFORE INSERT ON outbox_messages "
    "FOR EACH ROW EXECUTE FUNCTION test_break_owner_alerts()",
)
RESTORE_OWNER_ALERT_INSERTS = (
    "DROP TRIGGER IF EXISTS test_break_owner_alerts ON outbox_messages",
    "DROP FUNCTION IF EXISTS test_break_owner_alerts()",
)


async def _run_ddl(statements: tuple[str, ...]) -> None:
    async with TestingSessionLocal() as session:
        for statement in statements:
            await session.execute(text(statement))
        await session.commit()


@pytest_asyncio.fixture
async def owner_alert_outage(db: AsyncSession):
    """Returns (break, restore); a trigger left in place is dropped afterwards.

    Dropping the trigger needs an exclusive lock on outbox_messages, so the
    test session's open transaction is ended first.
    """
    broken = False

    async def break_inserts() -> None:
        nonlocal broken
        await _run_ddl(BREAK_OWNER_ALERT_INSERTS)
        broken = True

    async def restore_inserts() -> None:
        nonlocal broken
        await db.rollback()
        await _run_ddl(RESTORE_OWNER_ALERT_INSERTS)
        broken = False

    try:
        yield break_inserts, restore_inserts
    finally:
        if broken:
            await restore_inserts()


@pytest.fixture
def owner_alerts(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "7000001:owner-alerts-test-token-AAAAAAAAAAAA")
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", OWNER_CHAT)
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_CHAT_ID", None)
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_ALERTS_TOPIC_ID", None)


@pytest.fixture
def helpdesk_alerts(owner_alerts, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_CHAT_ID", GROUP_ID)
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_ALERTS_TOPIC_ID", ALERTS_TOPIC)


@pytest.fixture
def telegram_requests(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path.rsplit("/", 1)[-1], json.loads(request.content or b"{}")))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        outbox_service,
        "httpx",
        SimpleNamespace(
            AsyncClient=lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
            HTTPError=httpx.HTTPError,
            Response=httpx.Response,
        ),
    )
    return calls


async def _course(db: AsyncSession) -> Course:
    course = Course(title="Маникюр с нуля", price_self=5900, price_support=9900, is_published=True)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def _alerts(db: AsyncSession, kind: str) -> list[OutboxMessage]:
    db.expire_all()
    rows = await db.execute(
        select(OutboxMessage).where(OutboxMessage.kind == kind).order_by(OutboxMessage.created_at)
    )
    return list(rows.scalars().all())


def _order(course: Course, email: str, *, status: str = "pending", created_at: datetime) -> Order:
    return Order(
        course_id=course.id,
        course_title=course.title,
        tariff="self",
        customer_email=email,
        amount_kopecks=590000,
        currency="RUB",
        access_days=30,
        status=status,
        status_token_hash="0" * 64,
        created_at=created_at,
    )


# --- Routing -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_alerts_go_to_the_owner_chat_without_the_helpdesk(
    db: AsyncSession, owner_alerts, telegram_requests
):
    assert await outbox_service.enqueue_owner_telegram_alert(
        db, kind="owner_payment_alert", text="💰 Новая оплата", dedupe_key="routing:owner"
    )
    await db.commit()
    message = (await _alerts(db, "owner_payment_alert"))[0]
    assert message.recipient == str(OWNER_CHAT)
    assert message.payload == {"text": "💰 Новая оплата"}

    assert await outbox_service.process_outbox_batch(db) == 1
    assert telegram_requests == [("sendMessage", {"chat_id": str(OWNER_CHAT), "text": "💰 Новая оплата"})]


@pytest.mark.asyncio
async def test_alerts_go_to_the_payments_topic_with_the_helpdesk(
    db: AsyncSession, helpdesk_alerts, telegram_requests
):
    assert await outbox_service.enqueue_owner_telegram_alert(
        db, kind="owner_payment_alert", text="💰 Новая оплата", dedupe_key="routing:topic"
    )
    # A row queued before the change carries text only and still goes out.
    outbox_service.enqueue_outbox_message(
        db, kind="owner_payment_alert", channel="telegram", recipient=str(OWNER_CHAT),
        payload={"text": "старая строка"}, dedupe_key="routing:legacy",
    )
    await db.commit()

    message = await db.scalar(select(OutboxMessage).where(OutboxMessage.dedupe_key == "routing:topic"))
    assert message.recipient == str(GROUP_ID)
    assert message.payload == {"text": "💰 Новая оплата", "message_thread_id": ALERTS_TOPIC}

    assert await outbox_service.process_outbox_batch(db) == 2
    assert sorted(telegram_requests, key=lambda call: call[1]["text"]) == [
        ("sendMessage", {"chat_id": str(OWNER_CHAT), "text": "старая строка"}),
        ("sendMessage", {"chat_id": str(GROUP_ID), "text": "💰 Новая оплата",
                         "message_thread_id": ALERTS_TOPIC}),
    ]


@pytest.mark.asyncio
async def test_delivered_alerts_keep_their_text_and_topic_through_link_redaction(
    client: AsyncClient, db: AsyncSession, helpdesk_alerts, telegram_requests
):
    course = await _course(db)
    checkout = await client.post("/api/payments/guest-link", json={
        "course_id": str(course.id), "tariff": "self", "customer_email": "guest@example.com",
        "offer_accepted": True, "personal_data_consent": True,
        "attribution": {"first_touch": {"utm_source": "vk", "utm_campaign": "autumn"}},
    })
    assert checkout.status_code == 200
    alert = (await _alerts(db, "owner_order_created"))[0]
    alert_id, queued = alert.id, dict(alert.payload)

    assert await outbox_service.process_outbox_batch(db) == 1

    db.expire_all()
    delivered = await db.scalar(select(OutboxMessage).where(OutboxMessage.id == alert_id))
    assert delivered.status == "sent"
    # Alerts carry no token-bearing link, so the post-delivery redaction of
    # outbox payloads leaves them exactly as queued.
    assert delivered.payload == queued
    assert delivered.payload["message_thread_id"] == ALERTS_TOPIC
    assert "[REDACTED]" not in delivered.payload["text"]


@pytest.mark.asyncio
async def test_alerts_without_the_topic_stay_with_the_owner(
    db: AsyncSession, owner_alerts, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "TELEGRAM_HELPDESK_CHAT_ID", GROUP_ID)

    assert outbox_service.owner_alert_target() == (str(OWNER_CHAT), None)


@pytest.mark.asyncio
async def test_dead_letter_digest_follows_the_routing(db: AsyncSession, helpdesk_alerts):
    outbox_service.enqueue_outbox_message(
        db, kind="access_granted", recipient="x@example.com", payload={}, dedupe_key="dead",
    ).status = "dead_letter"
    await db.commit()

    await LifecycleService.schedule(db, now=datetime.utcnow())
    await db.commit()

    digest = (await _alerts(db, "system_alert"))[0]
    assert digest.recipient == str(GROUP_ID)
    assert digest.payload["message_thread_id"] == ALERTS_TOPIC


# --- Order created -----------------------------------------------------------


@pytest.mark.asyncio
async def test_guest_checkout_alerts_once_per_order_with_email_and_utm(
    client: AsyncClient, db: AsyncSession, helpdesk_alerts
):
    course = await _course(db)
    responses = []
    for _ in range(2):
        responses.append(await client.post(
            "/api/payments/guest-link",
            json={
                "course_id": str(course.id),
                "tariff": "self",
                "customer_email": "Guest@Example.com",
                "offer_accepted": True,
                "personal_data_consent": True,
                "attribution": {"first_touch": {"utm_source": "vk", "utm_campaign": "autumn"}},
            },
        ))
    assert all(response.status_code == 200 for response in responses)

    alerts = await _alerts(db, "owner_order_created")
    assert len(alerts) == 2
    first_order = responses[0].json()["order_id"]
    alert = next(item for item in alerts if item.payload["text"].endswith(first_order))
    text = alert.payload["text"]
    assert text.startswith("🧾 Новый заказ\n")
    assert "Сумма: 5 900 ₽" in text and "Курс: Маникюр с нуля" in text
    assert "Email: guest@example.com" in text
    assert "Источник: vk\nКампания: autumn\n" in text
    assert text.endswith(f"Заказ: {first_order}")
    assert alert.dedupe_key == f"order:{first_order.split('|')[1]}:created"
    assert alert.payload["message_thread_id"] == ALERTS_TOPIC
    assert await outbox_service.enqueue_owner_telegram_alert(
        db, kind="owner_order_created", text="повтор", dedupe_key=alert.dedupe_key
    ) is False


@pytest.mark.asyncio
async def test_logged_in_checkouts_alert_from_both_entry_points(
    client: AsyncClient, db: AsyncSession, owner_alerts
):
    course = await _course(db)
    user = User(email="member@example.com", email_verified_at=datetime.utcnow(),
                password_hash=get_password_hash("member-password-1"), role="student")
    db.add(user)
    await db.commit()
    headers = {"Authorization": f"Bearer {AuthService.create_tokens(user.id, user.token_version).access_token}"}

    link = await client.post("/api/payments/link",
                             json={"course_id": str(course.id), "tariff": "self"}, headers=headers)
    created = await client.post("/api/purchases/create",
                                json={"course_id": str(course.id), "tariff": "self"}, headers=headers)
    assert link.status_code == 200, link.text
    assert created.status_code == 200, created.text
    await db.commit()

    alerts = await _alerts(db, "owner_order_created")
    references = {alert.payload["text"].rsplit("Заказ: ", 1)[1] for alert in alerts}
    assert references == {link.json()["order_id"], created.json()["order_id"]}
    assert all("Email: member@example.com" in alert.payload["text"] for alert in alerts)
    assert all("Источник" not in alert.payload["text"] for alert in alerts)


@pytest.mark.asyncio
async def test_order_alert_is_skipped_without_any_alert_chat(
    client: AsyncClient, db: AsyncSession, owner_alerts, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", None)
    course = await _course(db)

    response = await client.post("/api/payments/guest-link", json={
        "course_id": str(course.id), "tariff": "self", "customer_email": "a@example.com",
        "offer_accepted": True, "personal_data_consent": True,
    })

    assert response.status_code == 200
    assert await _alerts(db, "owner_order_created") == []


# --- Abandoned orders --------------------------------------------------------


@pytest.mark.asyncio
async def test_abandoned_order_alert_once_and_only_for_recent_unpaid_orders(
    db: AsyncSession, owner_alerts
):
    now = datetime(2026, 11, 25, 12, 0)
    course = await _course(db)
    other_course = Course(title="Дизайн ногтей", price_self=4900, price_support=9900, is_published=True)
    db.add(other_course)
    await db.flush()
    minutes = timedelta(minutes=1)
    abandoned = _order(course, "slow@example.com", created_at=now - 90 * minutes)
    fresh = _order(course, "fresh@example.com", created_at=now - 10 * minutes)
    later = _order(course, "later@example.com", created_at=now - 50 * minutes)
    # Older than twice the delay at the first scan: the backlog left from before
    # the feature ran, never reported.
    backlog = _order(course, "backlog@example.com", created_at=now - 150 * minutes)
    paid = _order(course, "paid@example.com", status="paid", created_at=now - 90 * minutes)
    ancient = _order(course, "old@example.com", created_at=now - timedelta(days=2))
    retried = _order(course, "retry@example.com", created_at=now - 100 * minutes)
    retried_paid = _order(course, "Retry@Example.com", status="paid", created_at=now - 80 * minutes)
    # Paying for another course does not cover the unpaid one.
    switched = _order(course, "switch@example.com", created_at=now - 95 * minutes)
    switched_paid = _order(other_course, "switch@example.com", status="paid", created_at=now - 85 * minutes)
    db.add_all([abandoned, fresh, later, backlog, paid, ancient, retried, retried_paid, switched, switched_paid])
    await db.commit()
    abandoned_id, later_id, switched_id = abandoned.id, later.id, switched.id

    assert await schedule_abandoned_order_alerts(db, now=now) == 2
    await db.commit()
    assert await schedule_abandoned_order_alerts(db, now=now + 5 * minutes) == 0
    await db.commit()
    assert await schedule_abandoned_order_alerts(db, now=now + 15 * minutes) == 1
    await db.commit()
    assert await schedule_abandoned_order_alerts(db, now=now + 3 * timedelta(hours=1)) == 0
    await db.commit()

    alerts = {alert.dedupe_key: alert for alert in await _alerts(db, "owner_order_abandoned")}
    assert set(alerts) == {
        f"order:{abandoned_id}:abandoned",
        f"order:{switched_id}:abandoned",
        f"order:{later_id}:abandoned",
    }
    assert alerts[f"order:{abandoned_id}:abandoned"].payload["text"] == (
        "⏳ Заказ не оплачен\n"
        "Сумма: 5 900 ₽\n"
        "Курс: Маникюр с нуля\n"
        "Email: slow@example.com\n"
        f"Заказ: order|{abandoned_id}"
    )

@pytest.mark.asyncio
async def test_abandoned_order_alert_follows_the_setting_and_the_lifecycle_scan(
    db: AsyncSession, owner_alerts, monkeypatch: pytest.MonkeyPatch
):
    now = datetime.utcnow()
    course = await _course(db)
    db.add(_order(course, "slow@example.com", created_at=now - timedelta(minutes=45)))
    await db.commit()

    assert await schedule_abandoned_order_alerts(db, now=now) == 0  # default 60 minutes
    monkeypatch.setattr(settings, "ORDER_ABANDONED_ALERT_MINUTES", 0)
    assert await schedule_abandoned_order_alerts(db, now=now + timedelta(hours=1)) == 0
    monkeypatch.setattr(settings, "ORDER_ABANDONED_ALERT_MINUTES", 30)
    await LifecycleService.schedule(db, now=now)
    await db.commit()
    assert len(await _alerts(db, "owner_order_abandoned")) == 1


def test_abandoned_order_delay_is_bounded():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ORDER_ABANDONED_ALERT_MINUTES=-1)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ORDER_ABANDONED_ALERT_MINUTES=721)


# --- Activation --------------------------------------------------------------


async def _signed_webhook(client: AsyncClient, payload: dict) -> httpx.Response:
    headers = {"Sign": _make_signature(payload, "test-prodamus-hmac-secret-key-for-ci")}
    return await client.post("/api/payments/webhook", json=payload, headers=headers)


@pytest.mark.asyncio
async def test_activating_a_purchased_account_alerts_the_owner(
    client: AsyncClient, db: AsyncSession, owner_alerts
):
    course = await _course(db)
    checkout = await client.post("/api/payments/guest-link", json={
        "course_id": str(course.id), "tariff": "self", "customer_email": "new-buyer@example.com",
        "offer_accepted": True, "personal_data_consent": True,
    })
    order_reference = checkout.json()["order_id"]
    paid = await _signed_webhook(client, {
        "order_id": "prodamus-activation-1", "order_num": order_reference,
        "customer_email": "new-buyer@example.com", "sum": "5900", "currency": "rub",
        "payment_status": "success",
    })
    assert paid.status_code == 200, paid.text
    user_id = await db.scalar(select(User.id).where(User.email == "new-buyer@example.com"))

    for _ in range(2):
        db.expire_all()
        user = await db.get(User, user_id)
        response = await client.post("/api/auth/activate", json={
            "token": create_account_activation_token(user_id, user.token_version),
            "new_password": "new-buyer-password-1",
        })
        assert response.status_code == 200, response.text

    alerts = await _alerts(db, "owner_account_activated")
    assert len(alerts) == 1
    assert alerts[0].payload["text"] == (
        f"🔑 Аккаунт активирован\nEmail: new-buyer@example.com\nЗаказ: {order_reference}"
    )
    assert alerts[0].dedupe_key == f"user:{user_id}:activated"


@pytest.mark.asyncio
async def test_activating_an_account_without_purchase_is_not_reported(
    client: AsyncClient, db: AsyncSession, owner_alerts
):
    user = User(email="self-registered@example.com", password_hash=get_password_hash("password-123456"),
                role="student")
    db.add(user)
    await db.commit()

    response = await client.post("/api/auth/activate", json={
        "token": create_account_activation_token(user.id, user.token_version),
        "new_password": "self-registered-1",
    })

    assert response.status_code == 200, response.text
    assert await _alerts(db, "owner_account_activated") == []


@pytest.mark.asyncio
async def test_activation_alert_ignores_historical_manual_grants(
    client: AsyncClient, db: AsyncSession, owner_alerts
):
    course = await _course(db)
    granted_only = User(email="granted@example.com", password_hash=get_password_hash("password-123456"),
                        role="student")
    buyer = User(email="buyer@example.com", password_hash=get_password_hash("password-123456"),
                 role="student")
    db.add_all([granted_only, buyer])
    await db.flush()
    order = _order(course, "buyer@example.com", status="paid", created_at=datetime(2026, 11, 1))
    order.user_id = buyer.id
    db.add(order)
    await db.flush()
    expires = datetime.utcnow() + timedelta(days=30)
    db.add_all([
        Purchase(user_id=granted_only.id, course_id=course.id, tariff="self", amount_kopecks=0,
                 transaction_kind="manual_grant", payment_id="admin_grant_1", payment_status="success",
                 paid_at=datetime(2026, 11, 20), expires_at=expires),
        Purchase(user_id=buyer.id, course_id=course.id, order_id=order.id, tariff="self",
                 amount_kopecks=590000, payment_id="prodamus-real-1", payment_status="success",
                 paid_at=datetime(2026, 11, 1), expires_at=expires),
        # Newer than the real payment, but not a payment.
        Purchase(user_id=buyer.id, course_id=course.id, tariff="self", amount_kopecks=0,
                 transaction_kind="manual_grant", payment_id="admin_grant_2", payment_status="success",
                 paid_at=datetime(2026, 11, 22), expires_at=expires),
    ])
    await db.commit()
    order_id = order.id
    tokens = {
        user.email: create_account_activation_token(user.id, user.token_version)
        for user in (granted_only, buyer)
    }

    for token in tokens.values():
        response = await client.post("/api/auth/activate", json={
            "token": token, "new_password": "activated-password-1",
        })
        assert response.status_code == 200, response.text

    alerts = await _alerts(db, "owner_account_activated")
    assert [alert.payload["text"] for alert in alerts] == [
        f"🔑 Аккаунт активирован\nEmail: buyer@example.com\nЗаказ: order|{order_id}"
    ]


# --- Rejected payments -------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_payment_alert_names_the_checkout_email_and_the_form_email(
    client: AsyncClient, db: AsyncSession, owner_alerts
):
    course = await _course(db)
    checkout = await client.post("/api/payments/guest-link", json={
        "course_id": str(course.id), "tariff": "self", "customer_email": "checkout@example.com",
        "offer_accepted": True, "personal_data_consent": True,
    })
    reference = checkout.json()["order_id"]

    declined = await _signed_webhook(client, {
        "order_id": "prodamus-declined-1", "order_num": reference,
        "customer_email": "typed-on-form@example.com", "sum": "5900", "currency": "rub",
        "payment_status": "fail",
    })
    same_email = await _signed_webhook(client, {
        "order_id": "prodamus-declined-2", "order_num": reference,
        "customer_email": "CHECKOUT@example.com", "sum": "5900", "currency": "rub",
        "payment_status": "fail",
    })
    unknown_order = await _signed_webhook(client, {
        "order_id": "prodamus-declined-3", "order_num": f"order|{uuid4()}",
        "customer_email": "stranger@example.com", "sum": "5900", "currency": "rub",
        "payment_status": "fail",
    })
    assert declined.status_code == same_email.status_code == unknown_order.status_code == 422

    texts = {alert.payload["text"] for alert in await _alerts(db, "owner_payment_rejected")}
    assert len(texts) == 3
    assert (
        "ℹ️ Неуспешная попытка оплаты (статус: fail)\n"
        "Email: checkout@example.com\n"
        "Email в форме оплаты: typed-on-form@example.com\n"
        f"Заказ: {reference}"
    ) in texts
    assert (
        "ℹ️ Неуспешная попытка оплаты (статус: fail)\n"
        "Email: checkout@example.com\n"
        f"Заказ: {reference}"
    ) in texts
    assert any(
        alert_text.startswith(
            "ℹ️ Неуспешная попытка оплаты (статус: fail)\nEmail: stranger@example.com\nЗаказ: order|"
        )
        for alert_text in texts
    )


@pytest.mark.asyncio
async def test_failed_payment_alert_names_the_order_in_a_swapped_legacy_callback(
    client: AsyncClient, db: AsyncSession, owner_alerts
):
    course = await _course(db)
    checkout = await client.post("/api/payments/guest-link", json={
        "course_id": str(course.id), "tariff": "self", "customer_email": "checkout@example.com",
        "offer_accepted": True, "personal_data_consent": True,
    })
    reference = checkout.json()["order_id"]

    # Older callbacks carried the merchant reference in order_id and the
    # provider id in order_num.
    declined = await _signed_webhook(client, {
        "order_id": reference, "order_num": "prodamus-swapped-1",
        "customer_email": "form@example.com", "sum": "5900", "currency": "rub",
        "payment_status": "fail",
    })

    assert declined.status_code == 422
    texts = [alert.payload["text"] for alert in await _alerts(db, "owner_payment_rejected")]
    assert texts == [
        "ℹ️ Неуспешная попытка оплаты (статус: fail)\n"
        "Email: checkout@example.com\n"
        "Email в форме оплаты: form@example.com\n"
        f"Заказ: {reference}"
    ]


# --- An optional alert never undoes the customer action ----------------------


@pytest.mark.asyncio
async def test_a_failing_order_alert_keeps_every_checkout_and_is_recovered_once(
    client: AsyncClient, db: AsyncSession, owner_alerts, owner_alert_outage, caplog
):
    break_inserts, restore_inserts = owner_alert_outage
    course = await _course(db)
    member = User(email="member@example.com", email_verified_at=datetime.utcnow(),
                  password_hash=get_password_hash("member-password-1"), role="student")
    db.add(member)
    await db.commit()
    headers = {"Authorization": f"Bearer {AuthService.create_tokens(member.id, member.token_version).access_token}"}
    await break_inserts()
    caplog.set_level(logging.WARNING, logger="app.services.owner_alerts")

    guest = await client.post("/api/payments/guest-link", json={
        "course_id": str(course.id), "tariff": "self", "customer_email": "guest@example.com",
        "offer_accepted": True, "personal_data_consent": True,
    })
    link = await client.post("/api/payments/link",
                             json={"course_id": str(course.id), "tariff": "self"}, headers=headers)
    created = await client.post("/api/purchases/create",
                                json={"course_id": str(course.id), "tariff": "self"}, headers=headers)
    assert guest.status_code == link.status_code == created.status_code == 200
    # purchases/create runs in the test session (get_db override): commit it like get_db would.
    await db.commit()

    references = {guest.json()["order_id"], link.json()["order_id"], created.json()["order_id"]}
    async with TestingSessionLocal() as fresh:
        stored = {f"order|{order_id}" for order_id in (await fresh.execute(select(Order.id))).scalars()}
        assert stored == references
        assert await fresh.scalar(select(func.count()).select_from(OutboxMessage)) == 0
    assert "Owner alert not queued" in caplog.text
    assert "@" not in caplog.text

    await restore_inserts()
    now = datetime.utcnow()
    assert await schedule_missing_order_created_alerts(db, now=now) == 3
    await db.commit()
    assert await schedule_missing_order_created_alerts(db, now=now + timedelta(minutes=5)) == 0
    await LifecycleService.schedule(db, now=now + timedelta(minutes=10))
    await db.commit()

    alerts = await _alerts(db, "owner_order_created")
    assert {alert.payload["text"].rsplit("Заказ: ", 1)[1] for alert in alerts} == references
    assert len(alerts) == 3


@pytest.mark.asyncio
async def test_order_alert_recovery_skips_old_orders_and_needs_an_alert_chat(
    db: AsyncSession, owner_alerts, monkeypatch: pytest.MonkeyPatch
):
    now = datetime(2026, 11, 25, 12, 0)
    course = await _course(db)
    db.add_all([
        _order(course, "recent@example.com", created_at=now - timedelta(hours=23)),
        _order(course, "old@example.com", created_at=now - timedelta(hours=25)),
    ])
    await db.commit()

    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", None)
    assert await schedule_missing_order_created_alerts(db, now=now) == 0
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", OWNER_CHAT)
    assert await schedule_missing_order_created_alerts(db, now=now) == 1
    await db.commit()

    alerts = await _alerts(db, "owner_order_created")
    assert len(alerts) == 1 and "Email: recent@example.com" in alerts[0].payload["text"]


@pytest.mark.asyncio
async def test_a_failing_activation_alert_keeps_the_new_password(
    client: AsyncClient, db: AsyncSession, owner_alerts, owner_alert_outage
):
    break_inserts, _restore_inserts = owner_alert_outage
    course = await _course(db)
    checkout = await client.post("/api/payments/guest-link", json={
        "course_id": str(course.id), "tariff": "self", "customer_email": "buyer@example.com",
        "offer_accepted": True, "personal_data_consent": True,
    })
    paid = await _signed_webhook(client, {
        "order_id": "prodamus-outage-1", "order_num": checkout.json()["order_id"],
        "customer_email": "buyer@example.com", "sum": "5900", "currency": "rub",
        "payment_status": "success",
    })
    assert paid.status_code == 200, paid.text
    user_id = await db.scalar(select(User.id).where(User.email == "buyer@example.com"))
    version = (await db.get(User, user_id)).token_version
    token = create_account_activation_token(user_id, version)
    await break_inserts()

    response = await client.post("/api/auth/activate", json={
        "token": token, "new_password": "buyer-password-123",
    })

    assert response.status_code == 200, response.text
    async with TestingSessionLocal() as fresh:
        activated = await fresh.get(User, user_id)
        assert activated.email_verified_at is not None
        assert activated.token_version == version + 1
    assert await _alerts(db, "owner_account_activated") == []


@pytest.mark.asyncio
async def test_a_failing_order_lookup_keeps_the_planned_answer_to_a_declined_payment(
    client: AsyncClient, db: AsyncSession, owner_alerts, monkeypatch: pytest.MonkeyPatch
):
    course = await _course(db)
    checkout = await client.post("/api/payments/guest-link", json={
        "course_id": str(course.id), "tariff": "self", "customer_email": "checkout@example.com",
        "offer_accepted": True, "personal_data_consent": True,
    })
    reference = checkout.json()["order_id"]

    def unavailable(*_args, **_kwargs):
        raise OperationalError("SELECT orders", {}, Exception("lock timeout"))

    monkeypatch.setattr(owner_alerts_module, "select", unavailable)
    declined = await _signed_webhook(client, {
        "order_id": "prodamus-lookup-1", "order_num": reference,
        "customer_email": "form@example.com", "sum": "5900", "currency": "rub",
        "payment_status": "fail",
    })

    assert declined.status_code == 422
    texts = [alert.payload["text"] for alert in await _alerts(db, "owner_payment_rejected")]
    assert texts == [
        "ℹ️ Неуспешная попытка оплаты (статус: fail)\n"
        "Email: form@example.com\n"
        f"Заказ: {reference}"
    ]
