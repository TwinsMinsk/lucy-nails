"""Course prices and access duration need commerce.manage_pricing."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from app.services.auth_service import AuthService
from app.core.security import get_password_hash


async def _staff(db: AsyncSession, email: str, role_name: str, permissions: list[Permission]) -> dict[str, str]:
    user = User(email=email, password_hash=get_password_hash("staffpass1"), role="student")
    role = Role(name=role_name, description=role_name, is_system=True)
    role.permissions = permissions
    db.add_all([user, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
    await db.commit()
    token = AuthService.create_tokens(user.id, user.token_version).access_token
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def course(db: AsyncSession) -> Course:
    item = Course(title="Priced course", price_self=5900, price_support=11900, access_days=30)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    # Detach it: the endpoints share this session and must load the row themselves.
    db.expunge(item)
    return item


@pytest_asyncio.fixture
async def permissions(db: AsyncSession) -> dict[str, Permission]:
    content = Permission(name="content.manage", description="content")
    pricing = Permission(name="commerce.manage_pricing", description="pricing")
    db.add_all([content, pricing])
    await db.commit()
    return {"content": content, "pricing": pricing}


@pytest.mark.asyncio
async def test_content_manager_cannot_change_price_or_duration(
    client: AsyncClient, db: AsyncSession, course: Course, permissions
):
    headers = await _staff(db, "editor@example.com", "content_manager", [permissions["content"]])

    for change in ({"price_self": 100}, {"price_support": 100}, {"access_days": 3650}):
        response = await client.put(f"/api/admin/courses/{course.id}", json=change, headers=headers)
        assert response.status_code == 403, change
        assert response.json()["detail"] == "Permission required: commerce.manage_pricing"

    stored = await db.get(Course, course.id)
    assert (stored.price_self, stored.price_support, stored.access_days) == (5900, 11900, 30)


@pytest.mark.asyncio
async def test_content_manager_edits_course_when_terms_are_unchanged(
    client: AsyncClient, db: AsyncSession, course: Course, permissions
):
    headers = await _staff(db, "editor@example.com", "content_manager", [permissions["content"]])

    response = await client.put(
        f"/api/admin/courses/{course.id}",
        json={"title": "Renamed", "price_self": 5900, "price_support": 11900, "access_days": 30},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Renamed"
    pricing_audit = await db.scalar(
        select(AuditLog.id).where(AuditLog.action == "course.pricing.update")
    )
    assert pricing_audit is None


@pytest.mark.asyncio
async def test_content_manager_creates_course_only_with_default_terms(
    client: AsyncClient, db: AsyncSession, permissions
):
    headers = await _staff(db, "editor@example.com", "content_manager", [permissions["content"]])

    cheap = await client.post(
        "/api/admin/courses", json={"title": "Cheap", "price_self": 1}, headers=headers
    )
    assert cheap.status_code == 403
    default = await client.post(
        "/api/admin/courses",
        json={"title": "Default", "price_self": 5900, "price_support": 11900, "access_days": 30},
        headers=headers,
    )
    assert default.status_code == 200, default.text


@pytest.mark.asyncio
async def test_pricing_change_is_audited_with_old_and_new_values(
    client: AsyncClient, db: AsyncSession, course: Course, permissions
):
    headers = await _staff(
        db, "owner@example.com", "owner", [permissions["content"], permissions["pricing"]]
    )

    response = await client.put(
        f"/api/admin/courses/{course.id}",
        json={"price_self": 6900, "access_days": 45, "price_support": 11900},
        headers={**headers, "X-Correlation-ID": "pricing-test"},
    )

    assert response.status_code == 200, response.text
    entry = (
        await db.execute(select(AuditLog).where(AuditLog.action == "course.pricing.update"))
    ).scalar_one()
    owner_id = await db.scalar(select(User.id).where(User.email == "owner@example.com"))
    assert entry.actor_user_id == owner_id
    assert entry.object_id == str(course.id)
    assert entry.old_value == {"price_self": 5900, "access_days": 30}
    assert entry.new_value == {"price_self": 6900, "access_days": 45}
    assert entry.correlation_id == "pricing-test"
