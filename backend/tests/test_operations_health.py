from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.models.outbox import OutboxMessage
from app.services import operations_health_service as health


@pytest.mark.asyncio
async def test_monitor_requires_configured_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "MONITORING_TOKEN", "m" * 32)
    response = await client.get("/health/operations")
    assert response.status_code == 401
    assert "pending_messages" not in response.text
    monkeypatch.setattr(settings, "MONITORING_TOKEN", "")
    assert (await client.get("/health/operations")).status_code == 503


@pytest.mark.asyncio
async def test_monitor_detects_missing_worker_and_queue_lag(db, monkeypatch):
    redis = MagicMock()
    redis.get = AsyncMock(return_value=b"alive")
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=redis)
    context.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://isolated.test")
    monkeypatch.setattr(health.Redis, "from_url", lambda *args, **kwargs: context)
    assert (await health.operations_snapshot(db))["status"] == "ok"
    db.add(
        OutboxMessage(
            kind="access_granted",
            channel="email",
            recipient="test@example.test",
            payload={},
            dedupe_key="monitor-test",
            created_at=datetime.utcnow() - timedelta(minutes=3),
        )
    )
    await db.flush()
    snapshot = await health.operations_snapshot(db)
    assert snapshot["status"] == "degraded"
    assert snapshot["pending_messages"] == 1
    assert snapshot["oldest_pending_seconds"] >= 180
    redis.get.return_value = None
    assert not (await health.operations_snapshot(db))["worker_alive"]
