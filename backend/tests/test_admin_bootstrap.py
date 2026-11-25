import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.auth_security import AuthSession
from app.models.user import User
from app.services.admin_bootstrap import ensure_admin_user


@pytest.mark.asyncio
async def test_ensure_admin_user_creates_admin(db: AsyncSession):
    user = await ensure_admin_user(db, "Owner@Example.com", "StrongPass123!")
    await db.commit()

    result = await db.execute(select(User).where(User.email == "owner@example.com"))
    stored = result.scalar_one()
    assert user.id == stored.id
    assert stored.role == "admin"
    assert verify_password("StrongPass123!", stored.password_hash)


@pytest.mark.asyncio
async def test_ensure_admin_user_promotes_existing_user(db: AsyncSession):
    existing = User(
        email="student@example.com",
        password_hash="old-hash",
        role="student",
    )
    db.add(existing)
    await db.commit()

    user = await ensure_admin_user(db, "student@example.com", "NewStrongPass123!")
    await db.commit()

    assert user.id == existing.id
    assert user.role == "admin"
    assert verify_password("NewStrongPass123!", user.password_hash)


@pytest.mark.asyncio
async def test_promotion_revokes_every_earlier_session_and_token(
    client: AsyncClient, db: AsyncSession
):
    existing = User(
        email="squatter@example.com",
        password_hash=get_password_hash("squatterpass1"),
        role="student",
    )
    db.add(existing)
    await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": "squatter@example.com", "password": "squatterpass1"},
    )
    assert login.status_code == 200, login.text
    old_access = login.json()["access_token"]
    client.cookies.clear()

    user = await ensure_admin_user(db, "squatter@example.com", "OperatorPass123!")
    await db.commit()

    assert user.token_version == 1
    sessions = (
        await db.execute(select(AuthSession).where(AuthSession.user_id == user.id))
    ).scalars().all()
    assert sessions and all(item.revoked_at is not None for item in sessions)
    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {old_access}"}
    )
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_of_existing_admin_revokes_sessions(db: AsyncSession):
    admin = await ensure_admin_user(db, "owner@example.com", "FirstPass123456!")
    await db.commit()
    db.add(
        AuthSession(
            user_id=admin.id,
            refresh_token_hash="0" * 64,
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
    )
    await db.commit()

    again = await ensure_admin_user(db, "owner@example.com", "SecondPass123456!")
    await db.commit()

    assert again.token_version == 1
    active = await db.scalar(
        select(AuthSession.id).where(
            AuthSession.user_id == admin.id, AuthSession.revoked_at.is_(None)
        )
    )
    assert active is None


RAILWAY_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "railway" / "create_admin.py"


@pytest.mark.asyncio
async def test_railway_entry_point_revokes_sessions_of_an_existing_account(
    client: AsyncClient, db: AsyncSession
):
    existing = User(
        email="railway-owner@example.com",
        password_hash=get_password_hash("OldOwnerPass123!"),
        role="student",
    )
    db.add(existing)
    await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": "railway-owner@example.com", "password": "OldOwnerPass123!"},
    )
    old_access = login.json()["access_token"]
    client.cookies.clear()

    result = subprocess.run(
        [sys.executable, str(RAILWAY_SCRIPT), "railway-owner@example.com", "NewOwnerPass123!"],
        env={**os.environ, "DATABASE_URL": db.bind.url.render_as_string(hide_password=False)},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "NewOwnerPass123!" not in result.stdout + result.stderr
    db.expunge_all()
    stored = await db.scalar(select(User).where(User.email == "railway-owner@example.com"))
    assert stored.role == "admin"
    assert stored.token_version == 1
    assert verify_password("NewOwnerPass123!", stored.password_hash)
    active = await db.scalar(
        select(AuthSession.id).where(
            AuthSession.user_id == stored.id, AuthSession.revoked_at.is_(None)
        )
    )
    assert active is None
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_access}"})
    assert me.status_code == 401
