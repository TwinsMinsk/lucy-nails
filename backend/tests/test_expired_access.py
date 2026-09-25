"""GET /api/purchases/my/expired lists naturally expired, not yet renewed access."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.user import User
from app.services.auth_service import AuthService

URL = "/api/purchases/my/expired"


async def _user(db: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash=get_password_hash("password123"), role="student")
    db.add(user)
    await db.flush()
    return user


async def _course(db: AsyncSession, title: str, *, is_published: bool = True) -> Course:
    course = Course(
        title=title,
        price_self=5900,
        price_support=11900,
        is_published=is_published,
        cover_image_url=f"https://cdn.example.test/{title}.jpg",
    )
    db.add(course)
    await db.flush()
    return course


def _entitlement(
    user: User,
    course: Course,
    *,
    status: str,
    expires_at: datetime,
) -> Entitlement:
    return Entitlement(
        user_id=user.id,
        course_id=course.id,
        source="manual",
        tariff="self",
        status=status,
        starts_at=expires_at - timedelta(days=30),
        expires_at=expires_at,
    )


def _headers(user: User) -> dict[str, str]:
    token = AuthService.create_tokens(user.id, user.token_version).access_token
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_expired_access_is_listed_once_per_course_with_latest_expiry(
    client: AsyncClient, db: AsyncSession
):
    now = datetime.utcnow()
    user = await _user(db, "expired-listed@example.com")
    swept = await _course(db, "Swept")
    not_swept = await _course(db, "NotSwept")
    older = now - timedelta(days=40)
    latest = now - timedelta(days=5)
    db.add_all(
        [
            _entitlement(user, swept, status="expired", expires_at=older),
            _entitlement(user, swept, status="expired", expires_at=latest),
            # Lifecycle job has not run yet: still "active" but past expiry.
            _entitlement(user, not_swept, status="active", expires_at=now - timedelta(hours=1)),
        ]
    )
    await db.commit()

    response = await client.get(URL, headers=_headers(user))

    assert response.status_code == 200, response.text
    items = {item["course_id"]: item for item in response.json()}
    assert set(items) == {str(swept.id), str(not_swept.id)}
    swept_item = items[str(swept.id)]
    assert swept_item["course_title"] == "Swept"
    assert swept_item["cover_image_url"] == "https://cdn.example.test/Swept.jpg"
    assert swept_item["price_self"] == 5900
    assert datetime.fromisoformat(swept_item["expired_at"]) == latest


@pytest.mark.asyncio
async def test_renewed_course_is_not_listed(client: AsyncClient, db: AsyncSession):
    now = datetime.utcnow()
    user = await _user(db, "expired-renewed@example.com")
    course = await _course(db, "Renewed")
    db.add_all(
        [
            _entitlement(user, course, status="expired", expires_at=now - timedelta(days=3)),
            _entitlement(user, course, status="active", expires_at=now + timedelta(days=27)),
        ]
    )
    await db.commit()

    response = await client.get(URL, headers=_headers(user))

    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test_revoked_refunded_and_suspended_access_is_not_listed(
    client: AsyncClient, db: AsyncSession
):
    now = datetime.utcnow()
    user = await _user(db, "expired-revoked@example.com")
    revoked = await _course(db, "Revoked")
    refunded = await _course(db, "Refunded")
    suspended = await _course(db, "Suspended")
    refund_entitlement = _entitlement(
        user, refunded, status="revoked", expires_at=now - timedelta(days=1)
    )
    refund_entitlement.reason = "Refund approved"
    refund_entitlement.revoked_at = now - timedelta(days=10)
    db.add_all(
        [
            _entitlement(user, revoked, status="revoked", expires_at=now - timedelta(days=2)),
            refund_entitlement,
            _entitlement(user, suspended, status="suspended", expires_at=now - timedelta(days=2)),
        ]
    )
    await db.commit()

    response = await client.get(URL, headers=_headers(user))

    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test_course_with_a_current_suspension_is_not_offered_for_renewal(
    client: AsyncClient, db: AsyncSession
):
    now = datetime.utcnow()
    user = await _user(db, "expired-suspended@example.com")
    suspended = await _course(db, "SuspendedNow")
    unaffected = await _course(db, "OtherExpired")
    db.add_all(
        [
            # An old natural expiry would normally be offered for renewal...
            _entitlement(user, suspended, status="expired", expires_at=now - timedelta(days=40)),
            # ...but the current access is suspended by an admin.
            _entitlement(user, suspended, status="suspended", expires_at=now + timedelta(days=10)),
            _entitlement(user, unaffected, status="expired", expires_at=now - timedelta(days=3)),
        ]
    )
    await db.commit()

    response = await client.get(URL, headers=_headers(user))

    assert response.status_code == 200, response.text
    assert [item["course_id"] for item in response.json()] == [str(unaffected.id)]


@pytest.mark.asyncio
async def test_other_users_and_unpublished_courses_are_not_listed(
    client: AsyncClient, db: AsyncSession
):
    now = datetime.utcnow()
    viewer = await _user(db, "expired-viewer@example.com")
    other = await _user(db, "expired-other@example.com")
    course = await _course(db, "OtherUsers")
    hidden = await _course(db, "Unpublished", is_published=False)
    db.add_all(
        [
            _entitlement(other, course, status="expired", expires_at=now - timedelta(days=2)),
            _entitlement(viewer, hidden, status="expired", expires_at=now - timedelta(days=2)),
        ]
    )
    await db.commit()

    response = await client.get(URL, headers=_headers(viewer))

    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test_expired_courses_require_authentication(client: AsyncClient):
    response = await client.get(URL)

    assert response.status_code == 401
