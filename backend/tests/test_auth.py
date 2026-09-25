from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.legal import CONSENT_REQUIRED_DETAIL, CONSENT_VERSION
from app.models.user import User


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post("/api/auth/register", json={
        "email": "test_register_unique@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "offer_accepted": True,
        "personal_data_consent": True
    })
    if response.status_code != 201:
        print(f"Registration failed: {response.text}")
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test_register_unique@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    # Register first
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "offer_accepted": True,
        "personal_data_consent": True
    })
    
    # Login
    response = await client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert response.cookies.get("access_token")
    assert response.cookies.get("refresh_token")


@pytest.mark.asyncio
async def test_get_me_accepts_cookie_token(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "cookie-me@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "offer_accepted": True,
        "personal_data_consent": True
    })

    login_res = await client.post("/api/auth/login", json={
        "email": "cookie-me@example.com",
        "password": "password123"
    })

    response = await client.get(
        "/api/auth/me",
        cookies={"access_token": login_res.json()["access_token"]},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "cookie-me@example.com"


@pytest.mark.asyncio
async def test_refresh_accepts_cookie_token(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "cookie-refresh@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "offer_accepted": True,
        "personal_data_consent": True
    })

    login_res = await client.post("/api/auth/login", json={
        "email": "cookie-refresh@example.com",
        "password": "password123"
    })

    response = await client.post(
        "/api/auth/refresh",
        json={},
        cookies={"refresh_token": login_res.json()["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.cookies.get("access_token")
    assert response.cookies.get("csrf_token")


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    # Register
    await client.post("/api/auth/register", json={
        "email": "me@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "offer_accepted": True,
        "personal_data_consent": True
    })
    
    # Login
    login_res = await client.post("/api/auth/login", json={
        "email": "me@example.com",
        "password": "password123"
    })
    token = login_res.json()["access_token"]
    
    # Get Me
    response = await client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "consent",
    [
        {},
        {"offer_accepted": True},
        {"personal_data_consent": True},
        {"offer_accepted": False, "personal_data_consent": True},
    ],
)
async def test_register_requires_offer_and_personal_data_consent(
    client: AsyncClient, db: AsyncSession, consent: dict
):
    response = await client.post(
        "/api/auth/register",
        json={"email": "no-consent@example.com", "password": "password123", **consent},
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == CONSENT_REQUIRED_DETAIL
    assert (await db.execute(select(func.count(User.id)))).scalar_one() == 0


@pytest.mark.asyncio
async def test_register_records_consent(client: AsyncClient, db: AsyncSession):
    before = datetime.utcnow()

    response = await client.post(
        "/api/auth/register",
        json={
            "email": "consent@example.com",
            "password": "password123",
            "offer_accepted": True,
            "personal_data_consent": True,
        },
    )

    assert response.status_code == 201, response.text
    user = (await db.execute(select(User).where(User.email == "consent@example.com"))).scalar_one()
    assert user.consent_version == CONSENT_VERSION
    assert user.offer_accepted_at is not None and user.offer_accepted_at >= before
    assert user.personal_data_consent_at is not None and user.personal_data_consent_at >= before
