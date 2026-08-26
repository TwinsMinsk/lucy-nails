"""Idempotent persistence for first-party events."""

import uuid
import re
from datetime import datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent


EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s().-]*){10,}")
SENSITIVE_VALUE_FRAGMENTS = ("email=", "phone=", "token=", "password=")


def contains_sensitive_analytics_value(value: Any) -> bool:
    """Detect contact data and secret-like values anywhere in event input."""
    if isinstance(value, dict):
        return any(
            contains_sensitive_analytics_value(key)
            or contains_sensitive_analytics_value(nested)
            for key, nested in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(contains_sensitive_analytics_value(item) for item in value)
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    lowered = normalized.lower()
    return bool(
        EMAIL_PATTERN.search(normalized)
        or PHONE_PATTERN.search(normalized)
        or any(fragment in lowered for fragment in SENSITIVE_VALUE_FRAGMENTS)
    )


class AnalyticsService:
    @staticmethod
    async def record_event(
        db: AsyncSession,
        *,
        event_id: str,
        event_name: str,
        source: str,
        happened_at: datetime | None = None,
        anonymous_id: str | uuid.UUID | None = None,
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
        normalized_anonymous_id: str | None = None
        if anonymous_id is not None:
            try:
                normalized_anonymous_id = str(uuid.UUID(str(anonymous_id)))
            except (ValueError, AttributeError) as error:
                raise ValueError("Analytics anonymous_id must be a UUID") from error
        privacy_payload = {
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "utm_content": utm_content,
            "utm_term": utm_term,
            "properties": properties or {},
        }
        if contains_sensitive_analytics_value(privacy_payload):
            raise ValueError("Analytics events must not contain personal or secret data")
        statement = (
            insert(AnalyticsEvent)
            .values(
                id=uuid.uuid4(),
                event_id=event_id,
                event_name=event_name,
                source=source,
                happened_at=happened_at or datetime.utcnow(),
                anonymous_id=normalized_anonymous_id,
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
