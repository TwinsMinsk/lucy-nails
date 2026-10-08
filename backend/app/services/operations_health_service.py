from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy import func, select

from app.core.config import settings
from app.models.outbox import OutboxMessage


HEARTBEAT_KEY = "lucy:outbox:heartbeat"


async def record_worker_heartbeat() -> None:
    if not settings.REDIS_URL:
        return
    async with Redis.from_url(
        settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2
    ) as redis:
        await redis.set(HEARTBEAT_KEY, "alive", ex=120)


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
