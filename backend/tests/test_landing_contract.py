from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.user import User
from app.services.kinescope_service import kinescope_service


@pytest.mark.asyncio
async def test_no_published_course_is_authoritative_empty_publication(client):
    response = await client.get("/api/landing")
    assert response.status_code == 200, response.text
    assert response.json()["course"] is None
    assert response.json()["course_id"] is None
    assert response.json()["modules"] == []
    assert response.json()["gallery"] == []


@pytest.mark.asyncio
async def test_landing_course_snapshot_matches_hero_program_price_and_access(client, db):
    earlier = Course(title="Canonical course", price_self=7200, price_support=9000, access_days=45, is_published=True, created_at=datetime.utcnow() - timedelta(days=1))
    later = Course(title="Catalog first newest", price_self=12300, price_support=15000, access_days=20, is_published=True)
    db.add_all([earlier, later])
    await db.flush()
    visible = Module(course_id=earlier.id, title="Renamed CMS technique", order_index=1, is_published=True)
    hidden = Module(course_id=earlier.id, title="Hidden technique", order_index=2, is_published=False)
    db.add_all([visible, hidden])
    await db.flush()
    db.add_all([Lesson(module_id=visible.id, title="Visible", duration_seconds=600, order_index=1), Lesson(module_id=hidden.id, title="Hidden", duration_seconds=900, order_index=1)])
    await db.commit()
    response = await client.get("/api/landing")
    assert response.status_code == 200, response.text
    snapshot = response.json()["course"]
    assert snapshot == {"id": str(earlier.id), "title": "Canonical course", "price_self": 7200, "access_days": 45, "lessons_count": 1, "total_duration": 600}
    assert response.json()["course_id"] == snapshot["id"]
    assert [item["title"] for item in response.json()["modules"]] == ["Renamed CMS technique"]


@pytest.mark.asyncio
async def test_play_response_reports_configured_signed_url_lifetime(client, db, monkeypatch):
    user = User(email="ttl@example.com", email_verified_at=datetime.utcnow(), password_hash=get_password_hash("studentpass1"), role="student")
    course = Course(title="Preview", price_self=5000, price_support=10000, is_published=True)
    db.add_all([user, course])
    await db.flush()
    module = Module(course_id=course.id, title="Preview", order_index=1, is_published=True)
    db.add(module)
    await db.flush()
    lesson = Lesson(module_id=module.id, title="Preview", order_index=1, duration_seconds=60, is_preview=True, kinescope_video_id="fake-video")
    db.add(lesson)
    await db.commit()
    monkeypatch.setattr(settings, "KINESCOPE_DRM_TOKEN_TTL_SECONDS", 240)
    monkeypatch.setattr(kinescope_service, "get_embed_url", lambda **kwargs: "https://kinescope.io/embed/fake-video")
    login = await client.post("/api/auth/login", json={"email": user.email, "password": "studentpass1"})
    assert login.status_code == 200, login.text
    client.cookies.clear()
    response = await client.get(f"/api/lessons/{lesson.id}/play", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert response.status_code == 200, response.text
    assert response.json()["expires_in_seconds"] == 240
