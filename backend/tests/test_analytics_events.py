"""First-party analytics contracts: deduplication, attribution and PII safety."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent
from app.models.course import Course
from app.models.order import Order


@pytest.mark.asyncio
async def test_public_event_is_deduplicated_and_contains_no_pii(
    client: AsyncClient, db: AsyncSession
):
    event_id = str(uuid4())
    payload = {
        "event_id": event_id,
        "event_name": "landing_view",
        "source": "web",
        "anonymous_id": str(uuid4()),
        "utm_source": "instagram",
        "utm_campaign": "august_launch",
        "properties": {"path": "/", "variant": "main"},
    }

    first = await client.post("/api/analytics/events", json=payload)
    duplicate = await client.post("/api/analytics/events", json=payload)

    assert first.status_code == 202, first.text
    assert first.json() == {"accepted": True, "duplicate": False}
    assert duplicate.status_code == 202, duplicate.text
    assert duplicate.json() == {"accepted": True, "duplicate": True}
    rows = (
        await db.execute(select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].utm_source == "instagram"
    assert rows[0].properties == {"path": "/", "variant": "main"}

    pii = await client.post(
        "/api/analytics/events",
        json={
            **payload,
            "event_id": str(uuid4()),
            "properties": {"email": "student@example.com"},
        },
    )
    assert pii.status_code == 422, pii.text

    disguised_pii = await client.post(
        "/api/analytics/events",
        json={
            **payload,
            "event_id": str(uuid4()),
            "properties": {"label": "student@example.com"},
        },
    )
    assert disguised_pii.status_code == 422, disguised_pii.text

    pii_utm = await client.post(
        "/api/analytics/events",
        json={
            **payload,
            "event_id": str(uuid4()),
            "utm_campaign": "+7 999 123-45-67",
        },
    )
    assert pii_utm.status_code == 422, pii_utm.text

    unknown_property = await client.post(
        "/api/analytics/events",
        json={
            **payload,
            "event_id": str(uuid4()),
            "properties": {"unexpected": "value"},
        },
    )
    assert unknown_property.status_code == 422, unknown_property.text

    pii_anonymous_id = await client.post(
        "/api/analytics/events",
        json={
            **payload,
            "event_id": str(uuid4()),
            "anonymous_id": "student@example.com",
        },
    )
    assert pii_anonymous_id.status_code == 422, pii_anonymous_id.text


@pytest.mark.asyncio
async def test_public_event_rejects_server_only_financial_event(client: AsyncClient):
    response = await client.post(
        "/api/analytics/events",
        json={
            "event_id": str(uuid4()),
            "event_name": "purchase_confirmed",
            "source": "web",
            "anonymous_id": str(uuid4()),
            "properties": {},
        },
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_checkout_snapshots_first_and_last_touch_and_emits_server_events(
    client: AsyncClient, db: AsyncSession
):
    course = Course(
        title="Attributed course",
        price_self=12000,
        price_support=18000,
        is_published=True,
        access_days=30,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    anonymous_id = str(uuid4())

    response = await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "attributed@example.com",
            "attribution": {
                "anonymous_id": anonymous_id,
                "first_touch": {
                    "utm_source": "instagram",
                    "utm_campaign": "launch",
                },
                "last_touch": {
                    "utm_source": "telegram",
                    "utm_campaign": "reminder",
                },
            },
        },
    )
    assert response.status_code == 200, response.text
    order_id = UUID(response.json()["order_id"].split("|", 1)[1])
    order = await db.get(Order, order_id)
    assert order is not None
    assert order.course_title == "Attributed course"
    assert order.first_utm_source == "instagram"
    assert order.last_utm_source == "telegram"
    events = (
        await db.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.order_id == order.id)
            .order_by(AnalyticsEvent.event_name)
        )
    ).scalars().all()
    assert [event.event_name for event in events] == ["checkout_started", "payment_redirect"]
    assert all(event.anonymous_id == anonymous_id for event in events)

    pii_identifier = await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "safe-customer@example.com",
            "attribution": {"anonymous_id": "tracking@example.com"},
        },
    )
    assert pii_identifier.status_code == 422, pii_identifier.text
