"""A repeated manual grant with the same operation key grants once (review 2, item 4)."""

import asyncio
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.outbox import OutboxMessage
from app.models.user import User
from conftest import TestingSessionLocal, mfa_login


async def _setup(client: AsyncClient, db: AsyncSession, *, existing_student: bool = True):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="grant-key-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    course = Course(title="Grant Key Course", price_self=5000, price_support=10000, access_days=30)
    db.add_all([admin, course])
    student = None
    if existing_student:
        student = User(
            email="grant-key-student@example.com",
            email_verified_at=datetime.utcnow(),
            password_hash="unused",
            role="student",
        )
        db.add(student)
    await db.commit()
    login = await mfa_login(client, db, admin.email, "adminpass1")
    assert login.status_code == 200, login.text
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return headers, course, student


async def _counts() -> tuple[int, int]:
    async with TestingSessionLocal() as fresh:
        rows = await fresh.scalar(select(func.count(Entitlement.id)))
        emails = await fresh.scalar(
            select(func.count(OutboxMessage.id)).where(OutboxMessage.channel == "email")
        )
    return int(rows or 0), int(emails or 0)


def _use_separate_sessions() -> None:
    async def isolated_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = isolated_db


def _grant_payload(student: User, course: Course, **overrides) -> dict:
    return {
        "user_id": str(student.id),
        "course_id": str(course.id),
        "tariff": "self",
        "reason": "Gift from the student card",
        "idempotency_key": "grant-dialog-0001",
        **overrides,
    }


def _student_payload(course: Course, **overrides) -> dict:
    return {
        "email": "grant-key-student@example.com",
        "course_id": str(course.id),
        "access_days": 30,
        "reason": "Manual sale by support",
        "idempotency_key": "student-dialog-0001",
        **overrides,
    }


@pytest.mark.asyncio
async def test_grant_access_repeat_returns_the_first_grant(client: AsyncClient, db: AsyncSession):
    headers, course, student = await _setup(client, db)
    payload = _grant_payload(student, course)

    first = await client.post("/api/admin/grant-access", json=payload, headers=headers)
    second = await client.post("/api/admin/grant-access", json=payload, headers=headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json() == first.json()
    assert await _counts() == (1, 1)


@pytest.mark.asyncio
async def test_grant_access_concurrent_repeat_grants_once(client: AsyncClient, db: AsyncSession):
    headers, course, student = await _setup(client, db)
    payload = _grant_payload(student, course)
    _use_separate_sessions()

    responses = await asyncio.gather(
        *(client.post("/api/admin/grant-access", json=payload, headers=headers) for _ in range(2))
    )

    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json()["entitlement_id"] == responses[1].json()["entitlement_id"]
    assert await _counts() == (1, 1)


@pytest.mark.asyncio
async def test_grant_access_repeat_with_other_parameters_is_refused(
    client: AsyncClient, db: AsyncSession
):
    headers, course, student = await _setup(client, db)
    first = await client.post("/api/admin/grant-access", json=_grant_payload(student, course), headers=headers)
    assert first.status_code == 200, first.text

    other_days = await client.post(
        "/api/admin/grant-access", json=_grant_payload(student, course, access_days=60), headers=headers
    )
    other_reason = await client.post(
        "/api/admin/grant-access",
        json=_grant_payload(student, course, reason="Another reason here"),
        headers=headers,
    )

    assert other_days.status_code == 409, other_days.text
    assert "другими параметрами" in other_days.json()["detail"]
    assert other_reason.status_code == 409, other_reason.text
    assert await _counts() == (1, 1)


@pytest.mark.asyncio
async def test_grant_access_without_a_key_behaves_as_before(client: AsyncClient, db: AsyncSession):
    headers, course, student = await _setup(client, db)
    payload = _grant_payload(student, course)
    payload.pop("idempotency_key")

    for _ in range(2):
        response = await client.post("/api/admin/grant-access", json=payload, headers=headers)
        assert response.status_code == 200, response.text

    assert await _counts() == (2, 2)


@pytest.mark.asyncio
async def test_create_student_repeat_after_lost_response_returns_the_first_result(
    client: AsyncClient, db: AsyncSession
):
    headers, course, _ = await _setup(client, db, existing_student=False)
    payload = _student_payload(course)

    first = await client.post("/api/admin/students", json=payload, headers=headers)
    retry = await client.post("/api/admin/students", json=payload, headers=headers)

    assert first.status_code == 201, first.text
    assert retry.status_code == 201, retry.text
    assert retry.json() == first.json()
    assert first.json()["user_created"] is True
    assert await _counts() == (1, 1)

    changed = await client.post(
        "/api/admin/students", json=_student_payload(course, access_days=60), headers=headers
    )
    assert changed.status_code == 409, changed.text
    assert await _counts() == (1, 1)


@pytest.mark.asyncio
async def test_create_student_concurrent_repeat_grants_once(client: AsyncClient, db: AsyncSession):
    headers, course, _ = await _setup(client, db)
    payload = _student_payload(course)
    _use_separate_sessions()

    responses = await asyncio.gather(
        *(client.post("/api/admin/students", json=payload, headers=headers) for _ in range(2))
    )

    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json() == responses[1].json()
    assert await _counts() == (1, 1)
