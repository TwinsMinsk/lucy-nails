"""Manual notification retry is limited to failed messages (audit B13)."""

import asyncio
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.audit_log import AuditLog
from app.models.outbox import OutboxMessage
from app.models.user import User
from conftest import TestingSessionLocal


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="retry-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    db.add(admin)
    await db.commit()
    response = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _message(status: str, *, sent_at: datetime | None = None, locked_at: datetime | None = None) -> OutboxMessage:
    return OutboxMessage(
        kind="access_granted",
        channel="email",
        recipient="student@example.com",
        payload={"subject": "Access"},
        status=status,
        attempts=2,
        max_attempts=5,
        next_attempt_at=datetime.utcnow(),
        locked_at=locked_at,
        sent_at=sent_at,
        last_error="boom" if status in {"retry", "dead_letter"} else None,
        dedupe_key=f"retry-{status}",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["retry", "dead_letter"])
async def test_failed_notification_can_be_retried_and_is_audited(
    client: AsyncClient, db: AsyncSession, status: str
):
    headers = await _admin_headers(client, db)
    message = _message(status)
    db.add(message)
    await db.commit()

    response = await client.post(
        f"/api/admin/notifications/{message.id}/retry",
        json={"reason": "Provider recovered"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending"
    audit = (await db.execute(select(AuditLog).where(AuditLog.action == "notification.retry"))).scalar_one()
    assert audit.old_value == {"status": status, "attempts": 2}


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "processing", "sent"])
async def test_retry_of_active_or_sent_notification_is_refused(
    client: AsyncClient, db: AsyncSession, status: str
):
    headers = await _admin_headers(client, db)
    now = datetime.utcnow()
    message = _message(
        status,
        sent_at=now if status == "sent" else None,
        locked_at=now if status == "processing" else None,
    )
    db.add(message)
    await db.commit()
    message_id = message.id

    response = await client.post(
        f"/api/admin/notifications/{message_id}/retry",
        json={"reason": "Operator double click"},
        headers=headers,
    )

    assert response.status_code == 409, response.text
    assert status in response.json()["detail"]
    async with TestingSessionLocal() as fresh:
        stored = await fresh.get(OutboxMessage, message_id)
        assert stored.status == status
        assert stored.attempts == 2
        assert (stored.locked_at is not None) == (status == "processing")
        assert (
            await fresh.scalar(select(AuditLog.id).where(AuditLog.action == "notification.retry"))
        ) is None


@pytest.mark.asyncio
async def test_retry_waits_for_a_concurrent_worker_and_sees_its_result(
    client: AsyncClient, db: AsyncSession
):
    """A message the worker sends while the operator clicks must not be reset."""
    headers = await _admin_headers(client, db)
    message = _message("dead_letter")
    db.add(message)
    await db.commit()
    message_id = message.id

    async def isolated_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = isolated_db
    worker = TestingSessionLocal()
    try:
        await worker.execute(
            text("SELECT id FROM outbox_messages WHERE id = :id FOR UPDATE"),
            {"id": message_id},
        )
        request = asyncio.create_task(
            client.post(
                f"/api/admin/notifications/{message_id}/retry",
                json={"reason": "Operator retry during delivery"},
                headers=headers,
            )
        )
        await asyncio.sleep(0.5)
        assert not request.done()
        await worker.execute(
            text("UPDATE outbox_messages SET status = 'sent', sent_at = now() WHERE id = :id"),
            {"id": message_id},
        )
        await worker.commit()
        response = await request
    finally:
        await worker.close()

    assert response.status_code == 409, response.text
    async with TestingSessionLocal() as fresh:
        assert (await fresh.get(OutboxMessage, message_id)).status == "sent"
