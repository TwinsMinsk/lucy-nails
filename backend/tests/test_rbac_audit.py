import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from app.services.auth_service import AuthService


async def _staff_user(
    db: AsyncSession,
    *,
    email: str,
    role_name: str,
    permissions: list[str],
) -> User:
    user = User(
        email=email,
        password_hash=get_password_hash("staffpass1"),
        role="student",
    )
    role = Role(name=role_name, description=role_name, is_system=True)
    role.permissions = [Permission(name=name, description=name) for name in permissions]
    db.add_all([user, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
    await db.commit()
    await db.refresh(user)
    return user


async def _bearer(client: AsyncClient, user: User) -> dict[str, str]:
    login = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "staffpass1"},
    )
    assert login.status_code == 200, login.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_analyst_is_read_only(client: AsyncClient, db: AsyncSession):
    analyst = await _staff_user(
        db,
        email="analyst@example.com",
        role_name="analyst",
        permissions=["analytics.read"],
    )
    course = Course(title="RBAC Course", price_self=5000, price_support=10000, is_published=True)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    headers = await _bearer(client, analyst)

    analytics = await client.get("/api/admin/analytics", headers=headers)
    assert analytics.status_code == 200, analytics.text

    grant = await client.post(
        "/api/admin/grant-access",
        json={
            "user_id": str(analyst.id),
            "course_id": str(course.id),
            "tariff": "self",
            "reason": "Negative permission test",
        },
        headers=headers,
    )
    assert grant.status_code == 403


@pytest.mark.asyncio
async def test_content_manager_cannot_read_users(client: AsyncClient, db: AsyncSession):
    manager = await _staff_user(
        db,
        email="content-manager@example.com",
        role_name="content_manager",
        permissions=["content.manage"],
    )
    headers = await _bearer(client, manager)

    courses = await client.get("/api/admin/courses", headers=headers)
    assert courses.status_code == 200, courses.text
    users = await client.get("/api/admin/users", headers=headers)
    assert users.status_code == 403


@pytest.mark.asyncio
async def test_manual_access_is_written_to_audit_log(client: AsyncClient, db: AsyncSession):
    curator = await _staff_user(
        db,
        email="curator@example.com",
        role_name="curator",
        permissions=["access.manage"],
    )
    student = User(
        email="audit-student@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    course = Course(title="Audit Course", price_self=5000, price_support=10000, is_published=True)
    db.add_all([student, course])
    await db.commit()
    await db.refresh(student)
    await db.refresh(course)
    headers = await _bearer(client, curator)

    response = await client.post(
        "/api/admin/grant-access",
        json={
            "user_id": str(student.id),
            "course_id": str(course.id),
            "tariff": "self",
            "access_days": 14,
            "reason": "Compensation for a technical issue",
        },
        headers={**headers, "X-Correlation-ID": "audit-test-correlation"},
    )
    assert response.status_code == 200, response.text

    audit = (
        await db.execute(select(AuditLog).where(AuditLog.action == "entitlement.grant"))
    ).scalar_one()
    assert audit.actor_user_id == curator.id
    assert audit.object_type == "entitlement"
    assert audit.object_id == response.json()["entitlement_id"]
    assert audit.reason == "Compensation for a technical issue"
    assert audit.correlation_id == "audit-test-correlation"
    assert audit.new_value["access_days"] == 14


@pytest.mark.asyncio
async def test_cannot_remove_last_owner(client: AsyncClient, db: AsyncSession):
    owner = await _staff_user(
        db,
        email="owner@example.com",
        role_name="owner",
        permissions=["system.manage_roles"],
    )
    token = AuthService.create_tokens(owner.id, owner.token_version).access_token
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.put(
        f"/api/admin/team/users/{owner.id}/roles",
        json={"roles": [], "reason": "Owner account must remain protected"},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Cannot remove the last owner"
