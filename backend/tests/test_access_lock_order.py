"""Admin access actions and a full refund take locks in one order.

An extension used to lock the entitlement first and the purchase second, while
a full refund locks the purchase first and then the entitlement: run at the
same moment, they deadlocked and one request ended as a 500.
"""

import asyncio
import contextvars
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.user import User
from conftest import TestingSessionLocal, engine, mfa_login

BARRIER_TIMEOUT_SECONDS = 5

# Which request a session serves: "access" (admin access action) or "refund".
_request_role: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_role", default=None)


class _FirstLockBarrierSession(AsyncSession):
    """Production-like session (autoflush on) that pauses after its first lock.

    The access action pauses after the first lock it takes, the refund after it
    locked the purchase. Both then continue together, which is exactly the
    interleaving that deadlocked when the access action locked the entitlement
    before the purchase.
    """

    barrier: asyncio.Barrier | None = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._paused = False

    async def _pause_if_first_lock(self, statement) -> None:
        role = _request_role.get()
        if self._paused or role is None or self.barrier is None:
            return
        text = str(statement)
        is_row_lock = getattr(statement, "_for_update_arg", None) is not None
        if role == "access":
            locked = is_row_lock or "pg_advisory_xact_lock" in text
        else:
            locked = is_row_lock and "FROM purchases" in text
        if locked:
            self._paused = True
            await asyncio.wait_for(self.barrier.wait(), BARRIER_TIMEOUT_SECONDS)

    async def execute(self, statement, *args, **kwargs):
        result = await super().execute(statement, *args, **kwargs)
        await self._pause_if_first_lock(statement)
        return result

    async def scalar(self, statement, *args, **kwargs):
        result = await super().scalar(statement, *args, **kwargs)
        await self._pause_if_first_lock(statement)
        return result


# Same defaults as app.core.database.async_session_maker (autoflush on).
ProductionLikeSession = async_sessionmaker(
    engine, class_=_FirstLockBarrierSession, expire_on_commit=False
)


async def _production_like_db():
    async with ProductionLikeSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _seed(client: AsyncClient, db: AsyncSession):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="lock-order-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    student = User(
        email_verified_at=datetime.utcnow(),
        email="lock-order-student@example.com",
        password_hash="unused",
        role="student",
    )
    course = Course(title="Lock Order Course", price_self=5000, price_support=10000)
    db.add_all([admin, student, course])
    await db.flush()
    now = datetime.utcnow()
    purchase = Purchase(
        user_id=student.id,
        course_id=course.id,
        tariff="self",
        amount_kopecks=500000,
        payment_id="lock-order-payment",
        payment_status="success",
        paid_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add(purchase)
    await db.flush()
    entitlement = Entitlement(
        user_id=student.id,
        course_id=course.id,
        source_purchase_id=purchase.id,
        source="purchase",
        tariff="self",
        status="active",
        starts_at=now,
        expires_at=now + timedelta(days=30),
    )
    refund = RefundRequest(
        purchase_id=purchase.id,
        amount_kopecks=500000,
        reason="Full refund in the provider cabinet",
        status="submitted",
        provider_reference="P-LOCK-1",
        created_by_id=admin.id,
    )
    db.add_all([entitlement, refund])
    await db.commit()
    login = await mfa_login(client, db, admin.email, "adminpass1")
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return headers, entitlement.id, refund.id, purchase.id


async def _run_concurrently(client: AsyncClient, headers, access_call, refund_id):
    async def as_role(role, call):
        _request_role.set(role)
        return await call()

    _FirstLockBarrierSession.barrier = asyncio.Barrier(2)
    app.dependency_overrides[get_db] = _production_like_db
    try:
        # return_exceptions: a request that fails (the ASGI transport re-raises
        # server errors) must not leave the other one running unattended.
        return await asyncio.wait_for(
            asyncio.gather(
                as_role("access", access_call),
                as_role(
                    "refund",
                    lambda: client.put(
                        f"/api/admin/refunds/{refund_id}",
                        json={"status": "processed", "reason": "Confirmed in Prodamus"},
                        headers=headers,
                    ),
                ),
                return_exceptions=True,
            ),
            timeout=30,
        )
    finally:
        _FirstLockBarrierSession.barrier = None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action",
    ["extend", "suspend", "revoke-entitlement", "revoke-access"],
)
async def test_access_action_and_full_refund_complete_without_5xx(
    client: AsyncClient, db: AsyncSession, action: str
):
    headers, entitlement_id, refund_id, purchase_id = await _seed(client, db)
    calls = {
        "extend": lambda: client.post(
            f"/api/admin/entitlements/{entitlement_id}/extend",
            json={"days": 10, "reason": "Goodwill extension"},
            headers=headers,
        ),
        "suspend": lambda: client.post(
            f"/api/admin/entitlements/{entitlement_id}/suspend",
            json={"reason": "Student asked for a pause"},
            headers=headers,
        ),
        "revoke-entitlement": lambda: client.post(
            "/api/admin/revoke-entitlement",
            json={"entitlement_id": str(entitlement_id), "reason": "Access closed by support"},
            headers=headers,
        ),
        "revoke-access": lambda: client.post(
            "/api/admin/revoke-access",
            json={"purchase_id": str(purchase_id), "reason": "Chargeback confirmed"},
            headers=headers,
        ),
    }

    access_response, refund_response = await _run_concurrently(
        client, headers, calls[action], refund_id
    )

    # An exception here is a server error (e.g. a deadlock) surfaced by the transport.
    assert not isinstance(access_response, BaseException), repr(access_response)
    assert not isinstance(refund_response, BaseException), repr(refund_response)
    assert access_response.status_code < 500, access_response.text
    assert refund_response.status_code == 200, refund_response.text
    async with TestingSessionLocal() as fresh:
        refund = await fresh.get(RefundRequest, refund_id)
        entitlement = await fresh.get(Entitlement, entitlement_id)
    assert refund.status == "processed"
    # Whatever ran first, a fully refunded purchase leaves no usable access.
    assert entitlement.status in {"revoked", "suspended"}
    if action == "extend":
        # The refund won the purchase lock first, so the extension is refused.
        assert access_response.status_code == 422, access_response.text
        assert entitlement.status == "revoked"


@pytest.mark.asyncio
async def test_extension_audit_keeps_the_values_seen_under_the_lock(
    client: AsyncClient, db: AsyncSession
):
    headers, entitlement_id, _, _ = await _seed(client, db)
    async with TestingSessionLocal() as fresh:
        before = (await fresh.get(Entitlement, entitlement_id)).expires_at

    response = await client.post(
        f"/api/admin/entitlements/{entitlement_id}/extend",
        json={"days": 3, "reason": "Goodwill extension"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    from app.models.audit_log import AuditLog

    async with TestingSessionLocal() as fresh:
        audit = (
            await fresh.execute(select(AuditLog).where(AuditLog.action == "entitlement.extend"))
        ).scalar_one()
    assert audit.old_value == {"status": "active", "expires_at": before.isoformat()}
