import logging
from dataclasses import dataclass
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy import func, select

from app.core.config import settings
from app.models.outbox import OutboxMessage


logger = logging.getLogger(__name__)

HEARTBEAT_KEY = "lucy:outbox:heartbeat"
HEARTBEAT_TTL_SECONDS = 120


async def record_worker_heartbeat() -> None:
    if not settings.REDIS_URL:
        return
    async with Redis.from_url(
        settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2
    ) as redis:
        # The value is the UTC time of the beat, so readers can show its age.
        await redis.set(
            HEARTBEAT_KEY, datetime.utcnow().isoformat(), ex=HEARTBEAT_TTL_SECONDS
        )


@dataclass(frozen=True)
class WorkerHeartbeat:
    # "alive", "missing" (no beat within the TTL) or "unknown" (Redis unavailable).
    state: str
    age_seconds: int | None


async def read_worker_heartbeat() -> WorkerHeartbeat:
    """Read the outbox worker heartbeat without ever reporting an unknown as healthy."""
    if not settings.REDIS_URL:
        return WorkerHeartbeat(state="unknown", age_seconds=None)
    try:
        async with Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2
        ) as redis:
            value = await redis.get(HEARTBEAT_KEY)
    except Exception:
        logger.warning("Worker heartbeat could not be read from Redis")
        return WorkerHeartbeat(state="unknown", age_seconds=None)
    if not value:
        return WorkerHeartbeat(state="missing", age_seconds=None)
    raw = value.decode() if isinstance(value, bytes) else str(value)
    try:
        beat_at = datetime.fromisoformat(raw)
    except ValueError:
        # A beat written by an older worker carries no timestamp.
        return WorkerHeartbeat(state="alive", age_seconds=None)
    age = max(0, int((datetime.utcnow() - beat_at).total_seconds()))
    return WorkerHeartbeat(state="alive", age_seconds=age)


async def operations_snapshot(db) -> dict:
    worker_alive = False
    if settings.REDIS_URL:
        async with Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2
        ) as redis:
            worker_alive = bool(await redis.get(HEARTBEAT_KEY))
    pending = OutboxMessage.status.in_(["pending", "retry", "processing"])
    count, oldest = (
        await db.execute(
            select(
                func.count(OutboxMessage.id), func.min(OutboxMessage.created_at)
            ).where(pending)
        )
    ).one()
    failed = await db.scalar(
        select(func.count(OutboxMessage.id)).where(
            OutboxMessage.status == "dead_letter"
        )
    )
    age = max(0, int((datetime.utcnow() - oldest).total_seconds())) if oldest else 0
    healthy = worker_alive and age <= 120 and not failed
    return {
        "status": "ok" if healthy else "degraded",
        "worker_alive": worker_alive,
        "pending_messages": count,
        "oldest_pending_seconds": age,
        "dead_letters": failed or 0,
    }
