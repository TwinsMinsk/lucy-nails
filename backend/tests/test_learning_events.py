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
        email_verified_at=datetime.utcnow(),
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
        (
            await db.execute(
                select(AnalyticsEvent)
                .where(AnalyticsEvent.user_id == user.id)
                .order_by(AnalyticsEvent.event_name)
            )
        )
        .scalars()
        .all()
    )
    assert [event.event_name for event in events] == [
        "course_completed",
        "lesson_activity",
        "lesson_completed",
        "lesson_started",
    ]
    assert all(event.course_id == course.id for event in events)
    assert all(
        event.lesson_id == lesson.id
        for event in events
        if event.event_name != "course_completed"
    )


@pytest.mark.asyncio
async def test_repeat_lesson_visit_records_new_day_without_progress(
    client, db, monkeypatch
):
    from app.services import analytics_service

    now = datetime.utcnow()
    user = User(
        email="repeat-learning@example.com",
        password_hash="unused",
        role="student",
        email_verified_at=now,
    )
    course = Course(
        title="Repeat course", price_self=10, price_support=20, is_published=True
    )
    db.add_all([user, course])
    await db.flush()
    module = Module(
        course_id=course.id, title="Repeat module", order_index=1, is_published=True
    )
    db.add(module)
    await db.flush()
    lesson = Lesson(
        module_id=module.id,
        title="Repeat lesson",
        order_index=1,
        kinescope_video_id="repeat-video",
    )
    db.add(lesson)
    db.add(
        Purchase(
            user_id=user.id,
            course_id=course.id,
            tariff="self",
            amount_kopecks=1000,
            payment_id="repeat-payment",
            payment_status="success",
            expires_at=now + timedelta(days=30),
        )
    )
    await db.commit()
    headers = {
        "Authorization": f"Bearer {AuthService.create_tokens(user.id, user.token_version).access_token}"
    }
    first = await client.get(f"/api/lessons/{lesson.id}/play", headers=headers)
    assert first.status_code == 200, first.text
    duplicate = await client.get(f"/api/lessons/{lesson.id}", headers=headers)
    assert duplicate.status_code == 200, duplicate.text

    class NextDay(datetime):
        @classmethod
        def utcnow(cls):
            return now + timedelta(days=1)

    monkeypatch.setattr(analytics_service, "datetime", NextDay)
    repeated = await client.get(f"/api/lessons/{lesson.id}", headers=headers)
    assert repeated.status_code == 200, repeated.text
    events = (
        (
            await db.execute(
                select(AnalyticsEvent).where(AnalyticsEvent.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len([event for event in events if event.event_name == "lesson_started"]) == 1
    assert (
        len([event for event in events if event.event_name == "lesson_activity"]) == 2
    )
