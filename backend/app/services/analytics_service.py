"""Idempotent persistence for first-party events."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent


class AnalyticsService:
    @staticmethod
    async def record_event(
        db: AsyncSession,
        *,
        event_id: str,
        event_name: str,
        source: str,
        happened_at: datetime | None = None,
        anonymous_id: str | None = None,
        user_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
        course_id: uuid.UUID | None = None,
        lesson_id: uuid.UUID | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
        utm_term: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Persist an event once and return whether this call inserted it."""
        statement = (
            insert(AnalyticsEvent)
            .values(
                id=uuid.uuid4(),
                event_id=event_id,
                event_name=event_name,
                source=source,
                happened_at=happened_at or datetime.utcnow(),
                anonymous_id=anonymous_id,
                user_id=user_id,
                order_id=order_id,
                course_id=course_id,
                lesson_id=lesson_id,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
                utm_term=utm_term,
                properties=properties or {},
                created_at=datetime.utcnow(),
            )
            .on_conflict_do_nothing(index_elements=[AnalyticsEvent.event_id])
            .returning(AnalyticsEvent.id)
        )
        return (await db.scalar(statement)) is not None
