"""
Тесты для эндпоинта /lessons/{id}/play (Kinescope интеграция).
"""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from app.services.kinescope_service import kinescope_service


@pytest.mark.asyncio
async def test_get_lesson_play_url_unauthorized(client: AsyncClient):
    """Тест отказа без авторизации."""
    fake_lesson_id = str(uuid.uuid4())
    
    response = await client.get(f"/api/lessons/{fake_lesson_id}/play")
    
    # Должен вернуть 401 (неавторизован)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_kinescope_service_mock_mode():
    """Тест Mock-режима KinescopeService."""
    from app.models.user import User
    
    # Создаем фейкового пользователя
    fake_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed",
        role="student"
    )
    
    # В Mock-режиме должна возвращаться YouTube ссылка
    url = kinescope_service.get_embed_url("fake_video_id", fake_user)
    
    if kinescope_service.is_mock_mode:
        assert "youtube.com" in url
    else:
        assert "kinescope.io" in url
        assert fake_user.email in url


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
