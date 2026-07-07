"""
Тесты для эндпоинта /lessons/{id}/play (Kinescope интеграция).
"""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.purchase import Purchase
from app.models.user import User
from app.services.kinescope_service import kinescope_service


async def _seed_play(db: AsyncSession, *, with_purchase: bool, expired: bool = False) -> uuid.UUID:
    """Course→Module→Lesson (+опц. Purchase) и пользователь с известным паролем."""
    user = User(
        email="player@example.com",
        password_hash=get_password_hash("playerpass1"),
        role="student",
    )
    course = Course(title="Play Course", price_self=5000, price_support=10000, is_published=True)
    db.add_all([user, course])
    await db.flush()
    module = Module(course_id=course.id, title="M1", order_index=1, is_published=True)
    db.add(module)
    await db.flush()
    lesson = Lesson(
        module_id=module.id,
        title="L1",
        kinescope_video_id="vid-play",
        duration_seconds=600,
        order_index=1,
        is_preview=False,
    )
    db.add(lesson)
    if with_purchase:
        expires_at = datetime.utcnow() + (timedelta(days=-1) if expired else timedelta(days=10))
        db.add(
            Purchase(
                user_id=user.id,
                course_id=course.id,
                tariff="self",
                amount_kopecks=500000,
                payment_id=f"play-{'expired' if expired else 'active'}",
                payment_status="success",
                paid_at=datetime.utcnow(),
                expires_at=expires_at,
            )
        )
    await db.commit()
    await db.refresh(lesson)
    return lesson.id


async def _login_headers(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    token = r.json()["access_token"]
    client.cookies.clear()  # bearer-only, avoid CSRF on any later unsafe calls
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_lesson_play_url_unauthorized(client: AsyncClient):
    """Тест отказа без авторизации."""
    fake_lesson_id = str(uuid.uuid4())

    response = await client.get(f"/api/lessons/{fake_lesson_id}/play")

    # Должен вернуть 401 (неавторизован)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_play_happy_path_with_active_purchase(client: AsyncClient, db: AsyncSession):
    lesson_id = await _seed_play(db, with_purchase=True)
    headers = await _login_headers(client, "player@example.com", "playerpass1")

    r = await client.get(f"/api/lessons/{lesson_id}/play", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json().get("video_url")


@pytest.mark.asyncio
async def test_play_denied_without_purchase(client: AsyncClient, db: AsyncSession):
    lesson_id = await _seed_play(db, with_purchase=False)
    headers = await _login_headers(client, "player@example.com", "playerpass1")

    r = await client.get(f"/api/lessons/{lesson_id}/play", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_play_denied_with_expired_purchase(client: AsyncClient, db: AsyncSession):
    lesson_id = await _seed_play(db, with_purchase=True, expired=True)
    headers = await _login_headers(client, "player@example.com", "playerpass1")

    r = await client.get(f"/api/lessons/{lesson_id}/play", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_kinescope_service_mock_mode():
    """Тест Mock-режима KinescopeService."""
    from app.models.user import User

    fake_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed",
        role="student"
    )

    url = kinescope_service.get_embed_url("fake_video_id", fake_user)

    if kinescope_service.is_mock_mode:
        assert "youtube.com" in url
    else:
        assert "kinescope.io" in url
        # В реальном режиме всегда есть watermark; drmauthtoken — только когда настроен JWT.
        assert "watermark" in url


@pytest.mark.asyncio
async def test_kinescope_service_get_video_info():
    """Тест получения метаинформации о видео."""
    video_info = await kinescope_service.get_video_info("fake_video_id")
    
    # Должны быть ключи
    assert "title" in video_info
    assert "duration" in video_info
    assert "poster" in video_info
    
    # В mock режиме - конкретные значения
    if kinescope_service.is_mock_mode:
        assert video_info["title"] == "Demo Video"
        assert video_info["duration"] == 600
