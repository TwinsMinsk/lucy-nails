"""Administrative content readiness checks."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.rate_limit import limiter
from app.models.user import User
from app.services.content_health_service import ContentHealthService


router = APIRouter()


class VideoHealthItem(BaseModel):
    lesson_id: UUID
    lesson_title: str
    module_title: str
    course_id: UUID
    course_title: str
    video_id: str | None
    expected_duration_seconds: int
    provider_duration_seconds: float | None
    provider_status: str | None
    progress: int | None
    privacy_type: str | None
    status: str
    detail: str | None


class VideoHealthResponse(BaseModel):
    total: int
    ready: int
    problems: int
    items: list[VideoHealthItem]


@router.post("/content/video-health", response_model=VideoHealthResponse)
@limiter.limit("5/minute")
async def video_health(
    request: Request,
    course_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("content.manage")),
):
    items = await ContentHealthService.check_videos(db, course_id=course_id)
    ready = sum(item["status"] == "ready" for item in items)
    return VideoHealthResponse(
        total=len(items),
        ready=ready,
        problems=len(items) - ready,
        items=[VideoHealthItem(**item) for item in items],
    )
