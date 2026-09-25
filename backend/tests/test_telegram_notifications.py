"""One-time Telegram linking and lifecycle communication scheduling."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.services.auth import BotAuthService
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.analytics_event import AnalyticsEvent
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.outbox import OutboxMessage
from app.models.payment_event import PaymentEvent
from app.models.telegram_link import TelegramLinkToken
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.lifecycle_service import LifecycleService


@pytest.mark.asyncio
async def test_telegram_link_is_one_time_and_connects_account(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "lucy_test_bot")
    user = User(
        email="telegram-link@example.com",
        password_hash=get_password_hash("telegram-link-password"),
        role="student",
    )
    db.add(user)
    await db.commit()
    user_id = user.id
    token = AuthService.create_tokens(user.id, user.token_version).access_token
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/telegram/link", headers=headers)
    assert response.status_code == 201, response.text
    link = response.json()["url"]
    assert link.startswith("https://t.me/lucy_test_bot?start=")
    opaque_token = parse_qs(urlparse(link).query)["start"][0]
    assert len(opaque_token) >= 32

    telegram_user = SimpleNamespace(id=987654321, username="lucy_student", first_name="Anna")
    first = await BotAuthService.link_account(opaque_token, telegram_user)
    second = await BotAuthService.link_account(opaque_token, telegram_user)
    assert "успешно привязан" in first
    assert "уже использована" in second

    db.expire_all()
    linked = await db.get(User, user_id)
    assert linked.telegram_id == 987654321
    token_row = await db.scalar(select(TelegramLinkToken))
    assert token_row is not None and token_row.used_at is not None

    disconnect = await client.delete("/api/telegram/link", headers=headers)
    assert disconnect.status_code == 204, disconnect.text
    db.expire_all()
    assert (await db.get(User, user_id)).telegram_id is None


@pytest.mark.asyncio
async def test_lifecycle_scheduler_is_idempotent_and_expires_access(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 8, 26, 12, 0, 0)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_SUPPORT_GROUP_ID", -1001234567890)
    user = User(
        email="lifecycle@example.com",
        password_hash=get_password_hash("lifecycle-password"),
        role="student",
        telegram_id=123456789,
    )
    course = Course(
        title="Lifecycle course",
        price_self=10000,
        price_support=15000,
        is_published=True,
    )
    db.add_all([user, course])
    await db.flush()
    reminder = Entitlement(
        user_id=user.id,
        course_id=course.id,
        source="manual",
        tariff="self",
        status="active",
        starts_at=now - timedelta(days=23),
        expires_at=now + timedelta(days=7),
    )
    expired = Entitlement(
        user_id=user.id,
        course_id=course.id,
        source="purchase",
        tariff="support",
        status="active",
        starts_at=now - timedelta(days=31),
        expires_at=now - timedelta(minutes=1),
    )
    db.add_all([reminder, expired])
    await db.commit()

    first_count = await LifecycleService.schedule(db, now=now)
    await db.commit()
    second_count = await LifecycleService.schedule(db, now=now)
    await db.commit()
    assert first_count == 5
    assert second_count == 0
    await db.refresh(expired)
    assert expired.status == "expired"

    messages = (await db.execute(select(OutboxMessage))).scalars().all()
    assert sorted((message.kind, message.channel) for message in messages) == [
        ("access_expired", "email"),
        ("access_expired", "telegram"),
        ("access_expiry_reminder", "email"),
        ("access_expiry_reminder", "telegram"),
        ("telegram_group_remove", "telegram"),
    ]
    event = await db.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.event_name == "access_expired")
    )
    assert event is not None
    assert event.user_id == user.id


@pytest.mark.asyncio
async def test_lifecycle_owner_alert_skips_rejected_payments(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # Rejected payments get their own immediate alert; the digest must not
    # repeat them every hour forever.
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", 987654321)
    db.add(
        PaymentEvent(
            provider="prodamus",
            event_hash="f" * 64,
            event_type="success",
            processing_status="rejected",
            sanitized_payload={},
            error_code="amount_mismatch",
        )
    )
    await db.commit()

    scheduled = await LifecycleService.schedule(
        db,
        now=datetime(2026, 8, 26, 12, 0, 0),
    )
    await db.commit()

    assert scheduled == 0
    alert = await db.scalar(
        select(OutboxMessage).where(OutboxMessage.kind == "system_alert")
    )
    assert alert is None


@pytest.mark.asyncio
async def test_lifecycle_owner_alert_on_dead_letter_changes_and_daily(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_CHAT_ID", 987654321)

    def dead_letter(index: int) -> OutboxMessage:
        return OutboxMessage(
            kind="account_activation",
            channel="email",
            recipient=f"buyer{index}@example.com",
            payload={},
            status="dead_letter",
            attempts=5,
            dedupe_key=f"test-dead-letter:{index}",
        )

    async def alerts() -> list[OutboxMessage]:
        return list(
            (
                await db.execute(
                    select(OutboxMessage).where(OutboxMessage.kind == "system_alert")
                )
            ).scalars()
        )

    db.add(dead_letter(1))
    await db.commit()

    first = await LifecycleService.schedule(db, now=datetime(2026, 8, 26, 12, 0, 0))
    await db.commit()
    again_same_day = await LifecycleService.schedule(
        db, now=datetime(2026, 8, 26, 18, 0, 0)
    )
    await db.commit()
    assert (first, again_same_day) == (1, 0)
    [alert] = await alerts()
    assert alert.channel == "telegram"
    assert "не доставлено уведомлений: 1" in alert.payload["text"]

    db.add(dead_letter(2))
    await db.commit()
    after_new_dead_letter = await LifecycleService.schedule(
        db, now=datetime(2026, 8, 26, 19, 0, 0)
    )
    await db.commit()
    next_day = await LifecycleService.schedule(db, now=datetime(2026, 8, 27, 9, 0, 0))
    await db.commit()
    assert (after_new_dead_letter, next_day) == (1, 1)
    assert len(await alerts()) == 3
