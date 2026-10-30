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
# 10+ digits; a "+" or separators mean the value was written as a phone number.
PHONE_CANDIDATE_PATTERN = re.compile(r"\+?\d(?:[\s().-]*\+?\d){9,}")
# Ad systems put numeric IDs into UTM labels, so a bare digit run counts as a phone
# only if it can be one for our buyers: 7/8/9 or 37 first (RU, KZ, BY, Baltics,
# Caucasus) or 12-16 digits (a full international number, 15 at most, or a bank card).
BARE_PHONE_PATTERN = re.compile(r"[789]\d{9,10}|37\d{8,9}|\d{12,16}")
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
SENSITIVE_VALUE_FRAGMENTS = ("email=", "phone=", "token=", "password=")
ATTRIBUTION_MAX_LENGTH = 255


def _contains_phone(text: str) -> bool:
    for match in PHONE_CANDIDATE_PATTERN.finditer(UUID_PATTERN.sub(" ", text)):
        candidate = match.group()
        if not candidate.isdigit() or BARE_PHONE_PATTERN.fullmatch(candidate):
            return True
    return False


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
        or _contains_phone(normalized)
        or any(fragment in lowered for fragment in SENSITIVE_VALUE_FRAGMENTS)
    )


def clean_attribution_value(value: Any) -> str | None:
    """Return a UTM label that is safe to store, or None to drop it.

    Attribution is optional marketing data: it must never block a payment, so
    unusable values are dropped instead of being rejected.
    """
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if (
        not cleaned
        or len(cleaned) > ATTRIBUTION_MAX_LENGTH
        or not cleaned.isprintable()
        or contains_sensitive_analytics_value(cleaned)
    ):
        return None
    return cleaned


class AnalyticsService:
    @staticmethod
    async def record_lesson_activity(
        db: AsyncSession, *, user_id, course_id, lesson_id
    ):
        now = datetime.utcnow()
        return await AnalyticsService.record_event(
            db,
            event_id=f"lesson_activity:{user_id}:{lesson_id}:{now.date().isoformat()}",
            event_name="lesson_activity",
            source="server",
            happened_at=now,
            user_id=user_id,
            course_id=course_id,
            lesson_id=lesson_id,
            properties={},
        )

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
        if contains_sensitive_analytics_value(properties or {}):
            raise ValueError(
                "Analytics events must not contain personal or secret data"
            )
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
                utm_source=clean_attribution_value(utm_source),
                utm_medium=clean_attribution_value(utm_medium),
                utm_campaign=clean_attribution_value(utm_campaign),
                utm_content=clean_attribution_value(utm_content),
                utm_term=clean_attribution_value(utm_term),
                properties=properties or {},
                created_at=datetime.utcnow(),
            )
            .on_conflict_do_nothing(index_elements=[AnalyticsEvent.event_id])
            .returning(AnalyticsEvent.id)
        )
        return (await db.scalar(statement)) is not None
