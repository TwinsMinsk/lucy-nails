"""Team members are not counted as students (audit I5)."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.progress import Progress
from app.models.rbac import Role, UserRoleAssignment
from app.models.user import User
from conftest import mfa_login


@pytest.mark.asyncio
async def test_staff_with_student_role_are_excluded_from_student_counts(
    client: AsyncClient, db: AsyncSession
):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="counts-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    learner = User(email="learner@example.com", password_hash="unused", role="student")
    staff = [
        User(email=f"{name}@example.com", password_hash="unused", role="student")
        for name in ("analyst", "curator", "content_manager", "marketer", "admin-role")
    ]
    roles = [
        Role(name=name, description=name, is_system=True)
        for name in ("analyst", "curator", "content_manager", "marketer", "admin")
    ]
    db.add_all([admin, learner, *staff, *roles])
    await db.flush()
    db.add_all(
        [UserRoleAssignment(user_id=user.id, role_id=role.id) for user, role in zip(staff, roles)]
    )
    await db.commit()
    login = await mfa_login(client, db, admin.email, "adminpass1")
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    dashboard = await client.get("/api/admin/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_students"] == 1

    overview = await client.get("/api/admin/reports/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()["new_students"] == 1

    cohorts = await client.get("/api/admin/reports/cohorts", headers=headers)
    assert cohorts.status_code == 200, cohorts.text
    assert sum(row["students"] for row in cohorts.json()) == 1


@pytest.mark.asyncio
async def test_staff_are_excluded_from_active_students_and_the_students_list(
    client: AsyncClient, db: AsyncSession
):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="active-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    learner = User(email="active-learner@example.com", password_hash="unused", role="student")
    curator = User(email="active-curator@example.com", password_hash="unused", role="student")
    role = Role(name="curator", description="curator", is_system=True)
    course = Course(title="Active Course", price_self=5000, price_support=10000)
    db.add_all([admin, learner, curator, role, course])
    await db.flush()
    db.add(UserRoleAssignment(user_id=curator.id, role_id=role.id))
    module = Module(course_id=course.id, title="M", order_index=1, is_published=True)
    db.add(module)
    await db.flush()
    lesson = Lesson(module_id=module.id, title="L", duration_seconds=60, order_index=1)
    db.add(lesson)
    await db.flush()
    now = datetime.utcnow()
    for user in (admin, learner, curator):
        db.add(Progress(user_id=user.id, lesson_id=lesson.id, watched_seconds=10, is_completed=False, updated_at=now))
    await db.commit()
    login = await mfa_login(client, db, admin.email, "adminpass1")
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    progress = await client.get("/api/admin/reports/progress", headers=headers)
    assert progress.status_code == 200, progress.text
    assert progress.json()["active_students"] == 1

    students = await client.get("/api/admin/students", headers=headers)
    assert students.status_code == 200, students.text
    assert [item["email"] for item in students.json()["items"]] == ["active-learner@example.com"]