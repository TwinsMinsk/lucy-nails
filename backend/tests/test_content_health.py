"""Administrative Kinescope content readiness checks."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.user import User
from app.services.kinescope_service import kinescope_service


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    admin = User(
        email="content-health-admin@example.com",
        password_hash=get_password_hash("content-admin-pass"),
        role="admin",
    )
    db.add(admin)
    await db.commit()
    response = await client.post(
        "/api/auth/login",
        json={"email": admin.email, "password": "content-admin-pass"},
    )
    client.cookies.clear()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_admin_video_health_reports_every_failure_class(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    headers = await _admin_headers(client, db)
    course = Course(
        title="Health course",
        price_self=5000,
        price_support=10000,
        is_published=True,
    )
    db.add(course)
    await db.flush()
    module = Module(course_id=course.id, title="Module", order_index=1, is_published=True)
    db.add(module)
    await db.flush()
    db.add_all(
        [
            Lesson(module_id=module.id, title="Missing", order_index=1, duration_seconds=100),
            Lesson(
                module_id=module.id,
                title="Ready",
                order_index=2,
                duration_seconds=300,
                kinescope_video_id="ready",
            ),
            Lesson(
                module_id=module.id,
                title="Mismatch",
                order_index=3,
                duration_seconds=300,
                kinescope_video_id="mismatch",
            ),
            Lesson(
                module_id=module.id,
                title="Processing",
                order_index=4,
                duration_seconds=300,
                kinescope_video_id="processing",
            ),
            Lesson(
                module_id=module.id,
                title="Unavailable",
                order_index=5,
                duration_seconds=300,
                kinescope_video_id="unavailable",
            ),
        ]
    )
    await db.commit()

    async def video_info(video_id: str) -> dict:
        if video_id == "unavailable":
            raise RuntimeError("provider unavailable")
        if video_id == "processing":
            return {"status": "processing", "progress": 42, "duration": 0, "title": "P"}
        return {
            "status": "done",
            "progress": 100,
            "duration": 300 if video_id == "ready" else 420,
            "title": video_id,
            "privacy_type": "custom",
            "poster": "",
        }

    monkeypatch.setattr(kinescope_service, "get_video_info", video_info)
    response = await client.post(
        f"/api/admin/content/video-health?course_id={course.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 5
    assert body["ready"] == 1
    assert body["problems"] == 4
    assert {item["status"] for item in body["items"]} == {
        "missing_video_id",
        "ready",
        "duration_mismatch",
        "processing",
        "provider_error",
    }
