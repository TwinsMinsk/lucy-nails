"""Queries for the global Telegram support-group entitlement."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entitlement import Entitlement


async def has_active_support_entitlement(
    db: AsyncSession,
    user_id: UUID,
    *,
    exclude_entitlement_id: UUID | None = None,
    now: datetime | None = None,
) -> bool:
    current_time = now or datetime.utcnow()
    query = select(Entitlement.id).where(
        Entitlement.user_id == user_id,
        Entitlement.tariff == "support",
        Entitlement.status == "active",
        Entitlement.starts_at <= current_time,
        Entitlement.expires_at > current_time,
    )
    if exclude_entitlement_id is not None:
        query = query.where(Entitlement.id != exclude_entitlement_id)
    return await db.scalar(query.limit(1)) is not None
