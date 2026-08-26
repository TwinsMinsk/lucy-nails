import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User


async def _owner(db: AsyncSession) -> User:
    user = User(
        email="mfa-owner@example.com",
        password_hash=get_password_hash("StrongOwnerPass1!"),
        role="admin",
    )
    role = Role(name="owner", description="Owner", is_system=True)
    role.permissions = [
        Permission(name="system.manage_roles", description="Manage roles")
    ]
    db.add_all([user, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_owner_must_setup_and_use_mfa(client: AsyncClient, db: AsyncSession):
    owner = await _owner(db)
    credentials = {
        "email": owner.email,
        "password": "StrongOwnerPass1!",
    }

    initial_login = await client.post("/api/auth/login", json=credentials)
    assert initial_login.status_code == 403
    detail = initial_login.json()["detail"]
    assert detail["code"] == "mfa_setup_required"

    setup = await client.post(
        "/api/auth/mfa/setup",
        json={"setup_token": detail["setup_token"]},
    )
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["provisioning_uri"].startswith("otpauth://totp/")

    confirm = await client.post(
        "/api/auth/mfa/confirm",
        json={
            "setup_token": detail["setup_token"],
            "code": pyotp.TOTP(secret).now(),
        },
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["access_token"]
    assert len(confirm.json()["backup_codes"]) == 8

    client.cookies.clear()
    missing_code = await client.post("/api/auth/login", json=credentials)
    assert missing_code.status_code == 401
    assert missing_code.json()["detail"]["code"] == "mfa_code_required"

    login = await client.post(
        "/api/auth/login",
        json={**credentials, "mfa_code": pyotp.TOTP(secret).now()},
    )
    assert login.status_code == 200, login.text


@pytest.mark.asyncio
async def test_backup_code_is_single_use(client: AsyncClient, db: AsyncSession):
    owner = await _owner(db)
    credentials = {"email": owner.email, "password": "StrongOwnerPass1!"}
    initial = await client.post("/api/auth/login", json=credentials)
    setup_token = initial.json()["detail"]["setup_token"]
    setup = await client.post("/api/auth/mfa/setup", json={"setup_token": setup_token})
    confirmed = await client.post(
        "/api/auth/mfa/confirm",
        json={
            "setup_token": setup_token,
            "code": pyotp.TOTP(setup.json()["secret"]).now(),
        },
    )
    backup_code = confirmed.json()["backup_codes"][0]
    client.cookies.clear()

    first = await client.post(
        "/api/auth/login",
        json={**credentials, "mfa_code": backup_code},
    )
    assert first.status_code == 200, first.text
    client.cookies.clear()
    replay = await client.post(
        "/api/auth/login",
        json={**credentials, "mfa_code": backup_code},
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_user_can_list_and_revoke_active_session(
    client: AsyncClient, db: AsyncSession
):
    user = User(
        email="sessions@example.com",
        password_hash=get_password_hash("sessionpass1"),
        role="student",
    )
    db.add(user)
    await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "sessionpass1"},
        headers={"User-Agent": "Session test browser"},
    )
    assert login.status_code == 200, login.text
    access_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    client.cookies.clear()

    sessions = await client.get("/api/auth/sessions", headers=headers)
    assert sessions.status_code == 200, sessions.text
    assert len(sessions.json()) == 1
    assert sessions.json()[0]["user_agent"] == "Session test browser"

    revoked = await client.delete(
        f"/api/auth/sessions/{sessions.json()[0]['id']}",
        headers=headers,
    )
    assert revoked.status_code == 204
    rejected = await client.get("/api/auth/me", headers=headers)
    assert rejected.status_code == 401
