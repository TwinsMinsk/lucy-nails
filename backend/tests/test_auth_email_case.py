"""Case-insensitive email handling in auth (register/login/forgot-password).

A device that auto-capitalises an email (e.g. iPhone) must not lock a user
out of an account created with a differently-cased email, and case variants
must not be able to register duplicate accounts.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.models.outbox import OutboxMessage


@pytest.mark.asyncio
async def test_register_stores_email_lowercase(client: AsyncClient, db: AsyncSession):
    r = await client.post(
        "/api/auth/register",
        json={"email": "Maria@Example.com", "password": "password123", "offer_accepted": True, "personal_data_consent": True},
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "maria@example.com"

    result = await db.execute(select(User).where(User.email == "maria@example.com"))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_login_is_case_insensitive(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={"email": "Case@Example.com", "password": "password123", "offer_accepted": True, "personal_data_consent": True},
    )

    upper = await client.post(
        "/api/auth/login", json={"email": "CASE@example.com", "password": "password123"}
    )
    assert upper.status_code == 200, upper.text

    lower = await client.post(
        "/api/auth/login", json={"email": "case@example.com", "password": "password123"}
    )
    assert lower.status_code == 200, lower.text


@pytest.mark.asyncio
async def test_register_duplicate_is_case_insensitive(client: AsyncClient):
    r1 = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "password123", "offer_accepted": True, "personal_data_consent": True},
    )
    assert r1.status_code == 201, r1.text

    r2 = await client.post(
        "/api/auth/register",
        json={"email": "DUP@Example.com", "password": "password123", "offer_accepted": True, "personal_data_consent": True},
    )
    assert r2.status_code == 400
    assert r2.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_forgot_password_is_case_insensitive(client: AsyncClient, db: AsyncSession):
    await client.post(
        "/api/auth/register",
        json={"email": "forgot@example.com", "password": "password123", "offer_accepted": True, "personal_data_consent": True},
    )

    r = await client.post("/api/auth/forgot-password", json={"email": "FORGOT@Example.com"})
    assert r.status_code == 200
    messages = (await db.scalars(select(OutboxMessage).where(OutboxMessage.recipient == "forgot@example.com"))).all()
    assert len(messages) == 2
    assert all(message.kind == "email_verification" for message in messages)


@pytest.mark.asyncio
async def test_legacy_mixed_case_row_can_login_with_lowercase(client: AsyncClient, db: AsyncSession):
    # Simulates a pre-migration row created before emails were normalized.
    legacy_user = User(
        email="Legacy@Example.com",
        password_hash=get_password_hash("password123"),
        role="student",
    )
    db.add(legacy_user)
    await db.commit()

    r = await client.post(
        "/api/auth/login", json={"email": "legacy@example.com", "password": "password123"}
    )
    assert r.status_code == 200, r.text
