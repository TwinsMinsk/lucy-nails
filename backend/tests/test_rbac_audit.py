import asyncio
from datetime import datetime

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.admin_system import ROLE_CHANGE_LOCK_KEY, ensure_owner_removal_preserves_owner
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from app.core.database import get_db
from app.main import app
from conftest import TestingSessionLocal, mfa_headers


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
    capabilities = await client.get("/api/admin/team/me", headers=headers)
    assert capabilities.status_code == 200, capabilities.text
    assert capabilities.json()["roles"] == ["analyst"]
    assert capabilities.json()["permissions"] == ["analytics.read"]

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
    headers = await mfa_headers(client, db, owner, "staffpass1")

    team = await client.get("/api/admin/team/users", headers=headers)
    assert team.status_code == 200, team.text
    assert team.json()[0]["email"] == owner.email
    assert team.json()[0]["roles"] == ["owner"]

    response = await client.put(
        f"/api/admin/team/users/{owner.id}/roles",
        json={"roles": [], "reason": "Owner account must remain protected"},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Cannot remove the last owner"


@pytest.mark.asyncio
async def test_concurrent_owner_removal_preserves_one_owner(
    db: AsyncSession,
):
    permission = Permission(name="system.manage_roles", description="Manage roles")
    owner_role = Role(name="owner", description="Owner", is_system=True)
    owner_role.permissions = [permission]
    first = User(
        email="first-owner@example.com",
        password_hash=get_password_hash("ownerpass1"),
        role="admin",
    )
    second = User(
        email="second-owner@example.com",
        password_hash=get_password_hash("ownerpass2"),
        role="admin",
    )
    db.add_all([owner_role, first, second])
    await db.flush()
    db.add_all(
        [
            UserRoleAssignment(user_id=first.id, role_id=owner_role.id),
            UserRoleAssignment(user_id=second.id, role_id=owner_role.id),
        ]
    )
    await db.commit()
    sessions = async_sessionmaker(bind=db.bind, class_=AsyncSession, expire_on_commit=False)

    async def remove(target: User) -> int:
        async with sessions() as worker_db:
            try:
                await ensure_owner_removal_preserves_owner(worker_db)
                await worker_db.execute(
                    delete(UserRoleAssignment).where(
                        UserRoleAssignment.user_id == target.id,
                        UserRoleAssignment.role_id == owner_role.id,
                    )
                )
                await worker_db.commit()
                return 200
            except HTTPException as exc:
                await worker_db.rollback()
                return exc.status_code

    responses = await asyncio.gather(remove(first), remove(second))

    assert sorted(responses) == [200, 422]
    remaining = await db.scalar(
        select(func.count(UserRoleAssignment.id))
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .where(Role.name == "owner")
    )
    assert remaining == 1


async def _verified_legacy_admin(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash=get_password_hash("legacypass1"),
        role="admin",
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
@pytest.mark.parametrize("roles", [["curator"], []])
async def test_only_legacy_admin_cannot_drop_their_team_management(
    client: AsyncClient, db: AsyncSession, roles: list[str]
):
    legacy = await _verified_legacy_admin(db, "only-manager@example.com")
    db.add(Role(name="curator", description="Curator", is_system=True))
    await db.commit()
    headers = await mfa_headers(client, db, legacy, "legacypass1")

    response = await client.put(
        f"/api/admin/team/users/{legacy.id}/roles",
        json={"roles": roles, "reason": "Trying a narrower role"},
        headers=headers,
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "Cannot remove team management from the last account that has it"
    db.expunge_all()
    stored = await db.get(User, legacy.id)
    assert stored.role == "admin"
    assert stored.token_version == 0
    assignment = await db.scalar(
        select(UserRoleAssignment.id).where(UserRoleAssignment.user_id == legacy.id)
    )
    assert assignment is None


@pytest.mark.asyncio
async def test_dropping_legacy_admin_role_revokes_sessions_when_another_manager_exists(
    client: AsyncClient, db: AsyncSession
):
    owner = await _staff_user(
        db, email="owner@example.com", role_name="owner", permissions=["system.manage_roles"]
    )
    legacy = await _verified_legacy_admin(db, "legacy@example.com")
    headers = await mfa_headers(client, db, owner, "staffpass1")

    response = await client.put(
        f"/api/admin/team/users/{legacy.id}/roles",
        json={"roles": [], "reason": "Legacy admin leaves the team"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    db.expunge_all()
    stored = await db.get(User, legacy.id)
    assert stored.role == "student"
    assert stored.token_version == 1
    audit = await db.scalar(select(AuditLog).where(AuditLog.action == "team.roles.update"))
    assert audit.new_value["reauthentication_required"] is True


@pytest.mark.asyncio
async def test_manager_keeping_team_management_can_change_own_roles(
    client: AsyncClient, db: AsyncSession
):
    owner = await _staff_user(
        db, email="owner@example.com", role_name="owner", permissions=["system.manage_roles"]
    )
    await _verified_legacy_admin(db, "legacy@example.com")
    db.add(Role(name="curator", description="Curator", is_system=True))
    await db.commit()
    owner.email_verified_at = datetime.utcnow()
    await db.commit()
    headers = await mfa_headers(client, db, owner, "staffpass1")

    response = await client.put(
        f"/api/admin/team/users/{owner.id}/roles",
        json={"roles": ["owner", "curator"], "reason": "Owner also curates"},
        headers=headers,
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_concurrent_role_edits_by_one_admin_do_not_deadlock(
    client: AsyncClient, db: AsyncSession
):
    """A staff member's roles and the admin's own roles saved at the same time."""
    owner = await _staff_user(
        db, email="owner@example.com", role_name="owner", permissions=["system.manage_roles"]
    )
    staff = User(
        email="staff@example.com",
        password_hash=get_password_hash("staffpass1"),
        role="student",
        email_verified_at=datetime.utcnow(),
    )
    db.add_all([staff, Role(name="curator", description="Curator", is_system=True)])
    owner.email_verified_at = datetime.utcnow()
    await db.commit()
    headers = await mfa_headers(client, db, owner, "staffpass1")
    staff_id, owner_id = staff.id, owner.id

    async def isolated_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = isolated_db

    async def put_roles(user_id, roles):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
            return await other.put(
                f"/api/admin/team/users/{user_id}/roles",
                json={"roles": roles, "reason": "Concurrent team edit"},
                headers=headers,
            )

    async def waiting_for_role_lock() -> int:
        async with TestingSessionLocal() as probe:
            return await probe.scalar(
                text("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted")
            )

    async def wait_until_waiting(expected: int) -> None:
        for _ in range(200):
            if await waiting_for_role_lock() >= expected:
                return
            await asyncio.sleep(0.02)
        raise AssertionError("request did not reach the role-change lock")

    # Hold the role-change lock so both requests queue behind it in a known
    # order: the staff edit first, then the admin's own edit.
    async with TestingSessionLocal() as holder:
        await holder.execute(select(func.pg_advisory_xact_lock(ROLE_CHANGE_LOCK_KEY)))
        staff_edit = asyncio.create_task(put_roles(staff_id, ["curator"]))
        await wait_until_waiting(1)
        own_edit = asyncio.create_task(put_roles(owner_id, ["curator", "owner"]))
        await wait_until_waiting(2)
        await holder.rollback()

    responses = await asyncio.wait_for(
        asyncio.gather(staff_edit, own_edit, return_exceptions=True), timeout=30
    )

    assert [getattr(item, "status_code", item) for item in responses] == [200, 200]
