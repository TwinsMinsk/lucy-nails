"""Administrative checks for lesson video readiness."""

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.services.kinescope_service import kinescope_service


class ContentHealthService:
    @staticmethod
    async def check_videos(
        db: AsyncSession, *, course_id: UUID | None = None
    ) -> list[dict]:
        query = (
            select(Lesson, Module, Course)
            .join(Module, Module.id == Lesson.module_id)
            .join(Course, Course.id == Module.course_id)
            .order_by(Course.title, Module.order_index, Lesson.order_index)
        )
        if course_id is not None:
            query = query.where(Course.id == course_id)
        rows = (await db.execute(query)).all()
        semaphore = asyncio.Semaphore(5)

        async def check(row) -> dict:
            lesson, module, course = row
            base = {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "module_title": module.title,
                "course_id": course.id,
                "course_title": course.title,
                "video_id": lesson.kinescope_video_id,
                "expected_duration_seconds": lesson.duration_seconds,
                "provider_duration_seconds": None,
                "provider_status": None,
                "progress": None,
                "privacy_type": None,
                "detail": None,
            }
            if not lesson.kinescope_video_id:
                return {**base, "status": "missing_video_id"}
            try:
                async with semaphore:
                    info = await kinescope_service.get_video_info(
                        lesson.kinescope_video_id
                    )
            except Exception as exc:
                return {
                    **base,
                    "status": "provider_error",
                    "detail": str(exc)[:500],
                }

            provider_status = str(info.get("status") or "unknown")
            provider_duration = float(info.get("duration") or 0)
            enriched = {
                **base,
                "provider_status": provider_status,
                "provider_duration_seconds": provider_duration,
                "progress": int(info.get("progress") or 0),
                "privacy_type": info.get("privacy_type"),
            }
            if provider_status in {"error", "aborted"}:
                return {**enriched, "status": "provider_error"}
            if provider_status != "done":
                return {**enriched, "status": "processing"}
            expected = lesson.duration_seconds or 0
            tolerance = max(10.0, expected * 0.05)
            if expected and provider_duration and abs(expected - provider_duration) > tolerance:
                return {**enriched, "status": "duration_mismatch"}
            return {**enriched, "status": "ready"}

        return list(await asyncio.gather(*(check(row) for row in rows)))
