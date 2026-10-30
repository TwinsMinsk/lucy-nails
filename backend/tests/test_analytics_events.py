"""First-party analytics contracts: deduplication, attribution and PII safety."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.analytics_event import AnalyticsEvent
from app.models.course import Course
from app.models.order import Order
from app.models.user import User
from app.services.analytics_service import (
    AnalyticsService,
    clean_attribution_value,
    contains_sensitive_analytics_value,
)


CONTACT_VALUES = [
    "+79991234567",
    "+7 999 123-45-67",
    "8 (999) 123-45-67",
    "8-999-123-45-67",
    "79991234567",
    "89991234567",
    "9991234567",
    "375291234567",
    "380501234567",
    "37491234567",
    "+4915112345678",
    "4915112345678",
    "lead_79991234567",
    "+7\xa0999\xa0123\xa045\xa067",
    "8 999 123 45 67",
    "799​9123​4567",
    "79\xad99123⁠4567",
    "student@example.com",
    "student​@example.com",
    "phone=123",
    "ph​one=123",
]
# Allowed in UTM labels only: properties treat any 10+ digits as a phone.
NUMERIC_AD_IDS = [
    "1234567890",
    "12345678901",
    "ad_12345678901",
    "12345678901|5123456789|123456789",
    "12345678901234567",
    "7123456789012345678",
]
# Last group has digits only, so without UUID handling it looks like a phone.
DIGIT_HEAVY_UUID = "550e8400-e29b-41d4-a716-446655440000"


async def _published_course(db: AsyncSession) -> Course:
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
    return course


async def _guest_checkout(client: AsyncClient, course: Course, attribution):
    return await client.post(
        "/api/payments/guest-link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "customer_email": "attributed@example.com",
            "offer_accepted": True,
            "personal_data_consent": True,
            "attribution": attribution,
        },
    )


async def _order_events(db: AsyncSession, order_id: UUID) -> list[AnalyticsEvent]:
    return list(
        (await db.execute(select(AnalyticsEvent).where(AnalyticsEvent.order_id == order_id)))
        .scalars()
        .all()
    )


@pytest.mark.parametrize(
    "value",
    [
        "summer_sale",
        "123456789",
        DIGIT_HEAVY_UUID,
        f"course_{DIGIT_HEAVY_UUID}",
        f"курс{DIGIT_HEAVY_UUID}",
        f"cmp1234567 {DIGIT_HEAVY_UUID} 890",
    ],
)
def test_short_numbers_and_uuids_are_not_contact_data(value: str):
    assert contains_sensitive_analytics_value(value) is False


@pytest.mark.parametrize(
    "value",
    [
        *CONTACT_VALUES,
        *NUMERIC_AD_IDS,
        "4111111111111111",
        "12025550123",
        "4951234567",
        "3432123456",
        "0501234567",
    ],
)
def test_properties_rule_treats_any_ten_digits_as_sensitive(value: str):
    assert contains_sensitive_analytics_value(value) is True


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
        123,
        "x" * 256,
        "abc\x00def",
        "abc\x7fdef",
        "abc\tdef",
        "bad\ud800",
        *CONTACT_VALUES,
        f"79991234567 {DIGIT_HEAVY_UUID}",
    ],
)
def test_unusable_attribution_value_is_dropped(value):
    assert clean_attribution_value(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" 12345678901 ", "12345678901"),
        ("курс маникюра 2026", "курс маникюра 2026"),
        ("x" * 255, "x" * 255),
        ("курс\xa0маникюра", "курс маникюра"),
        ("весна 2026", "весна 2026"),
        ("весна　2026", "весна 2026"),
        ("👩‍💻 курс", "👩‍💻 курс"),
        (f"course_{DIGIT_HEAVY_UUID}", f"course_{DIGIT_HEAVY_UUID}"),
        (f"курс{DIGIT_HEAVY_UUID}", f"курс{DIGIT_HEAVY_UUID}"),
        (
            f"cmp1234567 {DIGIT_HEAVY_UUID} 890",
            f"cmp1234567 {DIGIT_HEAVY_UUID} 890",
        ),
        *((value, value) for value in NUMERIC_AD_IDS),
    ],
)
def test_usable_attribution_value_is_kept(value: str, expected: str):
    assert clean_attribution_value(value) == expected


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
        (
            await db.execute(
                select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id)
            )
        )
        .scalars()
        .all()
    )
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
@pytest.mark.parametrize("value", CONTACT_VALUES)
async def test_public_event_drops_contact_data_from_utm(
    client: AsyncClient, db: AsyncSession, value: str
):
    event_id = str(uuid4())

    response = await client.post(
        "/api/analytics/events",
        json={
            "event_id": event_id,
            "event_name": "landing_view",
            "source": "web",
            "anonymous_id": str(uuid4()),
            "utm_source": "yandex",
            "utm_term": value,
            "properties": {"path": "/"},
        },
    )

    assert response.status_code == 202, response.text
    event = await db.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id)
    )
    assert event.utm_source == "yandex"
    assert event.utm_term is None


@pytest.mark.asyncio
async def test_public_event_keeps_numeric_ad_id(client: AsyncClient, db: AsyncSession):
    event_id = str(uuid4())

    response = await client.post(
        "/api/analytics/events",
        json={
            "event_id": event_id,
            "event_name": "landing_view",
            "source": "web",
            "anonymous_id": str(uuid4()),
            "utm_content": "12345678901",
            "properties": {"path": "/"},
        },
    )

    assert response.status_code == 202, response.text
    event = await db.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id)
    )
    assert event.utm_content == "12345678901"


@pytest.mark.asyncio
async def test_landing_view_accepts_course_path_with_digit_heavy_uuid(
    client: AsyncClient,
):
    response = await client.post(
        "/api/analytics/events",
        json={
            "event_id": str(uuid4()),
            "event_name": "landing_view",
            "source": "web",
            "anonymous_id": str(uuid4()),
            "properties": {"path": f"/courses/{DIGIT_HEAVY_UUID}"},
        },
    )
    assert response.status_code == 202, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["12025550123", "4951234567", "12345678901"])
async def test_public_event_rejects_bare_number_in_properties(
    client: AsyncClient, value: str
):
    # "variant" is an allowed key, so only the value check can reject the event.
    response = await client.post(
        "/api/analytics/events",
        json={
            "event_id": str(uuid4()),
            "event_name": "landing_view",
            "source": "web",
            "anonymous_id": str(uuid4()),
            "properties": {"path": "/", "variant": value},
        },
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_record_event_never_stores_contact_data_in_utm(db: AsyncSession):
    event_id = str(uuid4())

    created = await AnalyticsService.record_event(
        db,
        event_id=event_id,
        event_name="purchase_confirmed",
        source="server",
        utm_source="yandex",
        utm_content="+79991234567",
    )
    await db.commit()

    assert created is True
    event = await db.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id)
    )
    assert event.utm_source == "yandex"
    assert event.utm_content is None


@pytest.mark.asyncio
async def test_record_event_still_rejects_contact_data_in_properties(db: AsyncSession):
    with pytest.raises(ValueError):
        await AnalyticsService.record_event(
            db,
            event_id=str(uuid4()),
            event_name="purchase_confirmed",
            source="server",
            properties={"label": "+79991234567"},
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["12025550123", "4951234567", "12345678901"])
async def test_record_event_rejects_bare_number_in_properties(
    db: AsyncSession, value: str
):
    with pytest.raises(ValueError):
        await AnalyticsService.record_event(
            db,
            event_id=str(uuid4()),
            event_name="purchase_confirmed",
            source="server",
            properties={"label": value},
        )


@pytest.mark.asyncio
async def test_record_event_accepts_uuid_in_properties_path(db: AsyncSession):
    created = await AnalyticsService.record_event(
        db,
        event_id=str(uuid4()),
        event_name="landing_view",
        source="server",
        properties={"path": f"/courses/{DIGIT_HEAVY_UUID}"},
    )
    assert created is True


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
@pytest.mark.parametrize(
    ("location", "expected_status"),
    [("pricing", 202), ("dashboard_renewal", 202), ("footer", 422)],
)
async def test_cta_click_accepts_known_locations_only(
    client: AsyncClient, location: str, expected_status: int
):
    response = await client.post(
        "/api/analytics/events",
        json={
            "event_id": str(uuid4()),
            "event_name": "cta_click",
            "source": "web",
            "anonymous_id": str(uuid4()),
            "properties": {"tariff": "self", "location": location},
        },
    )
    assert response.status_code == expected_status, response.text


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
            "offer_accepted": True,
            "personal_data_consent": True,
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
        (
            await db.execute(
                select(AnalyticsEvent)
                .where(AnalyticsEvent.order_id == order.id)
                .order_by(AnalyticsEvent.event_name)
            )
        )
        .scalars()
        .all()
    )
    assert [event.event_name for event in events] == [
        "checkout_started",
        "payment_redirect",
    ]
    assert all(event.anonymous_id == anonymous_id for event in events)


@pytest.mark.asyncio
async def test_checkout_keeps_numeric_ad_ids_in_attribution(
    client: AsyncClient, db: AsyncSession
):
    course = await _published_course(db)

    response = await _guest_checkout(
        client,
        course,
        {
            "anonymous_id": str(uuid4()),
            "first_touch": {"utm_source": "yandex", "utm_content": "12345678901"},
            "last_touch": {"utm_source": "yandex", "utm_term": "1234567890"},
        },
    )

    assert response.status_code == 200, response.text
    order_id = UUID(response.json()["order_id"].split("|", 1)[1])
    order = await db.get(Order, order_id)
    assert order.first_utm_content == "12345678901"
    assert order.last_utm_term == "1234567890"
    events = await _order_events(db, order_id)
    assert len(events) == 2
    assert all(event.utm_content == "12345678901" for event in events)


@pytest.mark.asyncio
async def test_checkout_keeps_labels_with_unicode_spaces_and_emoji(
    client: AsyncClient, db: AsyncSession
):
    course = await _published_course(db)

    response = await _guest_checkout(
        client,
        course,
        {
            "first_touch": {
                "utm_campaign": "курс\xa0маникюра",
                "utm_content": "👩‍💻 курс",
            },
        },
    )

    assert response.status_code == 200, response.text
    order_id = UUID(response.json()["order_id"].split("|", 1)[1])
    order = await db.get(Order, order_id)
    assert order.first_utm_campaign == "курс маникюра"
    assert order.first_utm_content == "👩‍💻 курс"


@pytest.mark.asyncio
@pytest.mark.parametrize("value", CONTACT_VALUES)
async def test_checkout_drops_contact_data_from_attribution(
    client: AsyncClient, db: AsyncSession, value: str
):
    course = await _published_course(db)
    touch = {"utm_source": "yandex", "utm_content": value, "utm_term": value}

    response = await _guest_checkout(
        client,
        course,
        {"anonymous_id": str(uuid4()), "first_touch": touch, "last_touch": touch},
    )

    assert response.status_code == 200, response.text
    order_id = UUID(response.json()["order_id"].split("|", 1)[1])
    order = await db.get(Order, order_id)
    assert order.first_utm_source == order.last_utm_source == "yandex"
    assert order.first_utm_content is None
    assert order.first_utm_term is None
    assert order.last_utm_content is None
    assert order.last_utm_term is None
    events = await _order_events(db, order_id)
    assert len(events) == 2
    assert all(event.utm_source == "yandex" for event in events)
    assert all(event.utm_content is None for event in events)
    assert all(event.utm_term is None for event in events)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "attribution",
    [
        "garbage",
        ["garbage"],
        {"anonymous_id": "1730000000000-abc123def"},
        {"anonymous_id": "tracking@example.com"},
        {"first_touch": "garbage"},
        {"last_touch": 123},
        {"first_touch": {"utm_source": 123}},
        {"first_touch": {"utm_content": "x" * 256}},
        {"last_touch": {"utm_content": "abc\x00def"}},
    ],
)
async def test_malformed_attribution_does_not_block_checkout(
    client: AsyncClient, db: AsyncSession, attribution
):
    course = await _published_course(db)

    response = await _guest_checkout(client, course, attribution)

    assert response.status_code == 200, response.text
    order_id = UUID(response.json()["order_id"].split("|", 1)[1])
    order = await db.get(Order, order_id)
    assert order.first_utm_source is None
    assert order.first_utm_content is None
    assert order.last_utm_content is None
    events = await _order_events(db, order_id)
    assert all(event.anonymous_id is None for event in events)


@pytest.mark.asyncio
async def test_malformed_anonymous_id_keeps_the_rest_of_attribution(
    client: AsyncClient, db: AsyncSession
):
    course = await _published_course(db)

    response = await _guest_checkout(
        client,
        course,
        {
            "anonymous_id": "1730000000000-abc123def",
            "first_touch": {"utm_source": "instagram"},
        },
    )

    assert response.status_code == 200, response.text
    order_id = UUID(response.json()["order_id"].split("|", 1)[1])
    assert (await db.get(Order, order_id)).first_utm_source == "instagram"


@pytest.mark.asyncio
async def test_authenticated_checkout_accepts_numeric_and_drops_contact_utm(
    client: AsyncClient, db: AsyncSession
):
    course = await _published_course(db)
    db.add(
        User(
            email="attributed-user@example.com",
            email_verified_at=datetime.utcnow(),
            password_hash=get_password_hash("password123"),
            role="student",
        )
    )
    await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": "attributed-user@example.com", "password": "password123"},
    )
    client.cookies.clear()

    response = await client.post(
        "/api/payments/link",
        json={
            "course_id": str(course.id),
            "tariff": "self",
            "attribution": {
                "first_touch": {
                    "utm_content": "12345678901",
                    "utm_term": "+79991234567",
                },
            },
        },
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 200, response.text
    order_id = UUID(response.json()["order_id"].split("|", 1)[1])
    order = await db.get(Order, order_id)
    assert order.first_utm_content == "12345678901"
    assert order.first_utm_term is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ["/admin", "/profile", "/courses/id/lessons/id", "/auth/reset", "/payment-success"],
)
async def test_collector_rejects_private_page_paths(client, path):
    response = await client.post(
        "/api/analytics/events",
        json={
            "event_id": str(uuid4()),
            "event_name": "landing_view",
            "source": "web",
            "anonymous_id": str(uuid4()),
            "properties": {"path": path},
        },
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_event_timestamp_is_normalized_to_utc(client, db):
    from datetime import datetime, timezone, timedelta

    instant = datetime.now(timezone.utc).replace(microsecond=0)
    event_id = str(uuid4())
    response = await client.post(
        "/api/analytics/events",
        json={
            "event_id": event_id,
            "event_name": "landing_view",
            "source": "web",
            "anonymous_id": str(uuid4()),
            "properties": {"path": "/courses/public-course"},
            "happened_at": instant.astimezone(timezone(timedelta(hours=3))).isoformat(),
        },
    )
    assert response.status_code == 202, response.text
    event = await db.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id)
    )
    assert event.happened_at == instant.replace(tzinfo=None)
