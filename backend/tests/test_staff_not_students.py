"""Team members are not counted as students (audit I5)."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.rbac import Role, UserRoleAssignment
from app.models.user import User


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
    login = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
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
