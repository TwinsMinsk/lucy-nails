from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.outbox_service as outbox_service
from app.models.outbox import DeliveryAttempt, OutboxMessage
from app.services.outbox_service import enqueue_outbox_message


@pytest.mark.asyncio
async def test_outbox_retries_failure_and_records_success(db: AsyncSession):
    message = enqueue_outbox_message(
        db,
        kind="access_granted",
        recipient="delivery@example.com",
        payload={"login_url": "https://example.test/login", "course_title": "Course"},
        dedupe_key="test:delivery-retry",
    )
    await db.commit()
    await db.refresh(message)

    processor = getattr(outbox_service, "process_outbox_batch", None)
    assert processor is not None, "outbox batch processor must exist"

    async def fail_delivery(_message: OutboxMessage) -> None:
        raise RuntimeError("email provider unavailable")

    processed = await processor(db, deliver=fail_delivery)
    assert processed == 1
    await db.refresh(message)
    assert message.status == "retry"
    assert message.attempts == 1
    assert message.last_error == "email provider unavailable"

    message.next_attempt_at = datetime.utcnow()
    await db.commit()

    delivered: list[str] = []

    async def succeed_delivery(current: OutboxMessage) -> None:
        delivered.append(current.recipient)

    processed = await processor(db, deliver=succeed_delivery)
    assert processed == 1
    await db.refresh(message)
    assert delivered == ["delivery@example.com"]
    assert message.status == "sent"
    assert message.attempts == 2
    assert message.sent_at is not None

    attempts = await db.execute(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.outbox_message_id == message.id)
        .order_by(DeliveryAttempt.attempt_number)
    )
    rows = attempts.scalars().all()
    assert [(row.attempt_number, row.status) for row in rows] == [
        (1, "failed"),
        (2, "sent"),
    ]


@pytest.mark.asyncio
async def test_outbox_delivers_telegram_channel(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    sent: list[tuple[str, str]] = []

    async def fake_telegram(recipient: str, text: str) -> None:
        sent.append((recipient, text))

    monkeypatch.setattr(outbox_service, "send_telegram_message", fake_telegram)
    message = enqueue_outbox_message(
        db,
        kind="access_expiry_reminder",
        channel="telegram",
        recipient="123456789",
        payload={"text": "Доступ закончится через 7 дней"},
        dedupe_key="telegram-reminder-test",
    )
    await db.commit()

    assert await outbox_service.process_outbox_batch(db) == 1
    await db.refresh(message)
    assert message.status == "sent"
    assert sent == [("123456789", "Доступ закончится через 7 дней")]
