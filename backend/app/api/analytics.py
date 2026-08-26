"""Public PII-free first-party event collector."""

from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.analytics_service import AnalyticsService


router = APIRouter()

PUBLIC_EVENT_NAMES = Literal["landing_view", "cta_click"]
FORBIDDEN_PROPERTY_FRAGMENTS = {
    "email",
    "phone",
    "password",
    "token",
    "card",
    "payment",
    "passport",
}


def _contains_forbidden_property(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(fragment in normalized for fragment in FORBIDDEN_PROPERTY_FRAGMENTS):
                return True
            if _contains_forbidden_property(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_property(item) for item in value)
    return False


class PublicAnalyticsEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_name: PUBLIC_EVENT_NAMES
    source: Literal["web"]
    happened_at: datetime = Field(default_factory=datetime.utcnow)
    anonymous_id: str = Field(..., min_length=8, max_length=128)
    course_id: UUID | None = None
    utm_source: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=255)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_content: str | None = Field(default=None, max_length=255)
    utm_term: str | None = Field(default=None, max_length=255)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def reject_pii_properties(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _contains_forbidden_property(value):
            raise ValueError("PII and payment data are not allowed in analytics events")
        if len(str(value)) > 4000:
            raise ValueError("Analytics properties are too large")
        return value

    @model_validator(mode="after")
    def validate_event_time(self):
        now = datetime.utcnow()
        happened_at = self.happened_at.replace(tzinfo=None)
        if happened_at < now - timedelta(days=7) or happened_at > now + timedelta(minutes=5):
            raise ValueError("Event timestamp is outside the accepted window")
        return self


class EventAccepted(BaseModel):
    accepted: bool
    duplicate: bool


@router.post(
    "/events",
    response_model=EventAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("60/minute")
async def collect_event(
    request: Request,
    data: PublicAnalyticsEvent,
    db: AsyncSession = Depends(get_db),
):
    created = await AnalyticsService.record_event(
        db,
        event_id=str(data.event_id),
        event_name=data.event_name,
        source=data.source,
        happened_at=data.happened_at.replace(tzinfo=None),
        anonymous_id=data.anonymous_id,
        course_id=data.course_id,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
        utm_content=data.utm_content,
        utm_term=data.utm_term,
        properties=data.properties,
    )
    await db.commit()
    return EventAccepted(accepted=True, duplicate=not created)
