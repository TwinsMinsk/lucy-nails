"""Queue and worker visibility in /admin/system/status (audit I2)."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.outbox import OutboxMessage
from app.models.user import User
from conftest import mfa_login
from app.services import operations_health_service as health


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="system-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    db.add(admin)
    await db.commit()
    response = await mfa_login(client, db, admin.email, "adminpass1")
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _redis_returning(monkeypatch: pytest.MonkeyPatch, value=None, error: Exception | None = None) -> MagicMock:
    redis = MagicMock()
    redis.get = AsyncMock(return_value=value, side_effect=error)
    redis.set = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=redis)
    context.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://isolated.test")
    monkeypatch.setattr(health.Redis, "from_url", lambda *args, **kwargs: context)
    return redis


async def _seed_queue(db: AsyncSession) -> None:
    now = datetime.utcnow()
    for index, (status, age) in enumerate(
        [
            ("pending", timedelta(minutes=1)),
            ("retry", timedelta(minutes=40)),
            ("retry", timedelta(minutes=5)),
            ("processing", timedelta(minutes=2)),
            ("dead_letter", timedelta(days=3)),
            ("sent", timedelta(days=10)),
        ]
    ):
        db.add(
            OutboxMessage(
                kind="access_granted",
                channel="email",
                recipient="student@example.test",
                payload={},
                status=status,
                dedupe_key=f"system-status-{index}",
                created_at=now - age,
            )
        )
    await db.commit()


@pytest.mark.asyncio
async def test_status_reports_every_undelivered_state_and_oldest_age(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    headers = await _admin_headers(client, db)
    await _seed_queue(db)
    _redis_returning(monkeypatch, (datetime.utcnow() - timedelta(seconds=30)).isoformat().encode())

    response = await client.get("/api/admin/system/status", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outbox_pending"] == 1
    assert body["outbox_retry"] == 2
    assert body["outbox_processing"] == 1
    assert body["outbox_dead_letter"] == 1
    # The 40-minute-old retry is the oldest undelivered message; dead letters and sent are not.
    assert 40 * 60 - 5 <= body["oldest_undelivered_seconds"] <= 40 * 60 + 60
    assert body["worker_heartbeat"] == "alive"
    assert body["worker_alive"] is True
    assert 25 <= body["worker_heartbeat_age_seconds"] <= 90


@pytest.mark.asyncio
async def test_status_reports_missing_worker(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    headers = await _admin_headers(client, db)
    _redis_returning(monkeypatch, None)

    body = (await client.get("/api/admin/system/status", headers=headers)).json()

    assert body["worker_heartbeat"] == "missing"
    assert body["worker_alive"] is False
    assert body["oldest_undelivered_seconds"] is None


@pytest.mark.asyncio
async def test_status_reports_unknown_heartbeat_when_redis_is_unavailable(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    headers = await _admin_headers(client, db)
    _redis_returning(monkeypatch, error=ConnectionError("redis down"))

    body = (await client.get("/api/admin/system/status", headers=headers)).json()

    assert body["worker_heartbeat"] == "unknown"
    assert body["worker_alive"] is None
    assert body["worker_heartbeat_age_seconds"] is None

    monkeypatch.setattr(settings, "REDIS_URL", "")
    body = (await client.get("/api/admin/system/status", headers=headers)).json()
    assert body["worker_heartbeat"] == "unknown"
    assert body["worker_alive"] is None


@pytest.mark.asyncio
async def test_heartbeat_written_by_worker_carries_its_time(monkeypatch: pytest.MonkeyPatch):
    redis = _redis_returning(monkeypatch, None)
    await health.record_worker_heartbeat()
    key, value = redis.set.await_args.args
    assert key == health.HEARTBEAT_KEY
    assert abs((datetime.utcnow() - datetime.fromisoformat(value)).total_seconds()) < 5
    # A beat from an older worker without a timestamp still counts as alive.
    redis.get.return_value = b"alive"
    beat = await health.read_worker_heartbeat()
    assert beat.state == "alive"
    assert beat.age_seconds is None
