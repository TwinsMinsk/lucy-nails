import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.outbox_service as outbox_service
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.outbox import DeliveryAttempt, OutboxMessage
from app.models.user import User
from app.services.outbox_service import enqueue_outbox_message
import app.workers.outbox as outbox_worker


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


@pytest.mark.asyncio
async def test_group_removal_keeps_member_banned(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[tuple[str, dict]] = []

    async def capture(method: str, payload: dict) -> None:
        calls.append((method, payload))

    monkeypatch.setattr(outbox_service, "_telegram_request", capture)

    await outbox_service.remove_telegram_group_member("-100123", "987654")

    assert calls == [
        ("banChatMember", {"chat_id": "-100123", "user_id": "987654"})
    ]


@pytest.mark.asyncio
async def test_worker_skips_stale_group_removal_when_support_access_is_active(
    db: AsyncSession,
):
    student = User(
        email="outbox-support@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
        telegram_id=445566,
    )
    course = Course(
        title="Outbox Support", price_self=5000, price_support=10000, is_published=True
    )
    db.add_all([student, course])
    await db.flush()
    now = datetime.utcnow()
    db.add(
        Entitlement(
            user_id=student.id,
            course_id=course.id,
            source="manual",
            tariff="support",
            status="active",
            starts_at=now,
            expires_at=now + timedelta(days=30),
        )
    )
    message = enqueue_outbox_message(
        db,
        kind="telegram_group_remove",
        channel="telegram",
        recipient=str(student.telegram_id),
        payload={"group_id": -100123, "user_id": str(student.id)},
        dedupe_key="stale-support-removal",
    )
    await db.commit()

    delivered: list[str] = []

    async def capture_delivery(current: OutboxMessage) -> None:
        delivered.append(current.recipient)

    assert await outbox_service.process_outbox_batch(db, deliver=capture_delivery) == 1
    await db.refresh(message)
    attempt = await db.scalar(
        select(DeliveryAttempt).where(DeliveryAttempt.outbox_message_id == message.id)
    )
    assert delivered == []
    assert message.status == "sent"
    assert attempt is not None and attempt.status == "skipped"


@pytest.mark.asyncio
async def test_outbox_claims_entire_batch_before_external_delivery(db: AsyncSession):
    for index in range(2):
        enqueue_outbox_message(
            db,
            kind="access_granted",
            recipient=f"worker-{index}@example.test",
            payload={"login_url": "https://example.test/login", "course_title": "Course"},
            dedupe_key=f"worker-claim:{index}",
        )
    await db.commit()

    first_delivery_started = asyncio.Event()
    release_first_worker = asyncio.Event()
    delivered: list[str] = []

    async def slow_delivery(message: OutboxMessage) -> None:
        delivered.append(message.recipient)
        if len(delivered) == 1:
            first_delivery_started.set()
            await release_first_worker.wait()

    worker_sessions = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with worker_sessions() as worker_one, worker_sessions() as worker_two:
        first_task = asyncio.create_task(
            outbox_service.process_outbox_batch(worker_one, deliver=slow_delivery, limit=2)
        )
        await asyncio.wait_for(first_delivery_started.wait(), timeout=5)
        try:
            second_count = await outbox_service.process_outbox_batch(
                worker_two, deliver=slow_delivery, limit=2
            )
            assert second_count == 0
        finally:
            release_first_worker.set()
            first_count = await first_task

    assert first_count == 2
    assert sorted(delivered) == ["worker-0@example.test", "worker-1@example.test"]


@pytest.mark.asyncio
async def test_worker_delivers_existing_outbox_when_lifecycle_scan_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    sessions: list[object] = []

    @asynccontextmanager
    async def fake_session_factory():
        session = object()
        sessions.append(session)
        yield session

    async def failing_schedule(_db: object) -> int:
        raise RuntimeError("lifecycle scan failed")

    delivered: list[object] = []

    async def successful_delivery(db: object) -> int:
        delivered.append(db)
        return 1

    monkeypatch.setattr(outbox_worker, "async_session_maker", fake_session_factory)
    monkeypatch.setattr(outbox_worker.LifecycleService, "schedule", failing_schedule)
    monkeypatch.setattr(outbox_worker, "process_outbox_batch", successful_delivery)
    monkeypatch.setattr(settings, "LIFECYCLE_SCAN_SECONDS", 0)

    processed, next_scan = await outbox_worker.run_iteration(0.0)

    assert processed == 1
    assert next_scan > 0
    assert len(sessions) == 2
    assert delivered == [sessions[1]]
