"""Dashboard «payment errors» counts distinct unresolved incidents (audit I22)."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.payment_event import PaymentEvent
from app.models.user import User


def _event(key: str, status: str, received_at: datetime, *, external: str | None, reference: str | None) -> PaymentEvent:
    return PaymentEvent(
        event_hash=key,
        external_event_id=external,
        order_reference=reference,
        event_type="success",
        processing_status=status,
        error_code="amount_mismatch" if status == "rejected" else None,
        sanitized_payload={},
        received_at=received_at,
        processed_at=received_at,
    )


@pytest.mark.asyncio
async def test_payment_errors_count_unresolved_incidents_in_last_30_days(
    client: AsyncClient, db: AsyncSession
):
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="incidents-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    db.add(admin)
    now = datetime.utcnow()
    db.add_all(
        [
            # One rejected payment delivered three times (attempt 1..3): one incident.
            _event("a1", "rejected", now - timedelta(hours=3), external="7001", reference="order|A"),
            _event("a2", "rejected", now - timedelta(hours=2), external="7001", reference="order|A"),
            _event("a3", "rejected", now - timedelta(hours=1), external="7001", reference="order|A"),
            # Rejected, then the same order was paid: resolved.
            _event("b1", "rejected", now - timedelta(days=2), external="7002", reference="order|B"),
            _event("b2", "processed", now - timedelta(days=1), external="7003", reference="order|B"),
            # A duplicate payment for a paid order needs reconciliation: one incident.
            _event("c1", "financial_incident", now - timedelta(days=3), external="7004", reference="order|C"),
            # Older than 30 days: out of the dashboard window, still unresolved.
            _event("d1", "rejected", now - timedelta(days=45), external="7005", reference="order|D"),
            # A rejection without any reference is its own incident.
            _event("e1", "rejected", now - timedelta(days=4), external=None, reference=None),
        ]
    )
    await db.commit()
    login = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    dashboard = await client.get("/api/admin/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["payment_errors"] == 3

    reconciliation = await client.get("/api/admin/reconciliation", headers=headers)
    assert reconciliation.status_code == 200, reconciliation.text
    assert reconciliation.json()["processed_payment_errors"] == 4


@pytest.mark.asyncio
async def test_legacy_field_order_is_normalised_before_deduplication(
    client: AsyncClient, db: AsyncSession
):
    """Old callbacks put the order reference in order_id and the payment id in order_num."""
    admin = User(
        email_verified_at=datetime.utcnow(),
        email="legacy-incidents-admin@example.com",
        password_hash=get_password_hash("adminpass1"),
        role="admin",
    )
    db.add(admin)
    now = datetime.utcnow()
    db.add_all(
        [
            # Two separate extra payments for one order, old field order.
            _event("l1", "financial_incident", now - timedelta(hours=5), external="order|X", reference="P-1"),
            _event("l2", "financial_incident", now - timedelta(hours=4), external="order|X", reference="P-2"),
            # An old-order rejection later resolved by a new-order processed delivery.
            _event("l3", "rejected", now - timedelta(hours=3), external="order|Y", reference="P-3"),
            _event("l4", "processed", now - timedelta(hours=2), external="P-4", reference="order|Y"),
        ]
    )
    await db.commit()
    login = await client.post(
        "/api/auth/login", json={"email": admin.email, "password": "adminpass1"}
    )
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    dashboard = await client.get("/api/admin/dashboard", headers=headers)
    assert dashboard.json()["payment_errors"] == 2
    reconciliation = await client.get("/api/admin/reconciliation", headers=headers)
    assert reconciliation.json()["processed_payment_errors"] == 2