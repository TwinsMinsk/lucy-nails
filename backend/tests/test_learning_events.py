"""Server-owned learning events cannot be forged by the browser."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.analytics_event import AnalyticsEvent
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.purchase import Purchase
from app.models.user import User
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_play_and_completion_emit_idempotent_learning_events(
    client: AsyncClient, db: AsyncSession
):
    user = User(
        email="learning-events@example.com",
        password_hash=get_password_hash("learning-events-password"),
        role="student",
    )
    course = Course(
        title="Learning events course",
        price_self=9000,
        price_support=14000,
        is_published=True,
    )
    db.add_all([user, course])
    await db.flush()
    module = Module(
        course_id=course.id,
        title="Only module",
        order_index=1,
        is_published=True,
    )
    db.add(module)
    await db.flush()
    lesson = Lesson(
        module_id=module.id,
        title="Only lesson",
        kinescope_video_id="learning-event-video",
        duration_seconds=120,
        order_index=1,
    )
    db.add(lesson)
    await db.flush()
    db.add(
        Purchase(
            user_id=user.id,
            course_id=course.id,
            tariff="self",
            amount_kopecks=900_000,
            payment_id="learning-events-payment",
            payment_status="success",
            paid_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    )
    await db.commit()
    token = AuthService.create_tokens(user.id, user.token_version).access_token
    headers = {"Authorization": f"Bearer {token}"}

    first_play = await client.get(f"/api/lessons/{lesson.id}/play", headers=headers)
    second_play = await client.get(f"/api/lessons/{lesson.id}/play", headers=headers)
    assert first_play.status_code == 200, first_play.text
    assert second_play.status_code == 200, second_play.text
    completion = await client.post(
        f"/api/lessons/{lesson.id}/progress",
        json={"watched_seconds": 120, "is_completed": True},
        headers=headers,
    )
    repeated = await client.post(
        f"/api/lessons/{lesson.id}/progress",
        json={"watched_seconds": 120, "is_completed": True},
        headers=headers,
    )
    assert completion.status_code == 200, completion.text
    assert repeated.status_code == 200, repeated.text

    events = (
        await db.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.user_id == user.id)
            .order_by(AnalyticsEvent.event_name)
        )
    ).scalars().all()
    assert [event.event_name for event in events] == [
        "course_completed",
        "lesson_completed",
        "lesson_started",
    ]
    assert all(event.course_id == course.id for event in events)
    assert all(event.lesson_id == lesson.id for event in events if event.event_name != "course_completed")
