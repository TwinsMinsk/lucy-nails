import asyncio
from datetime import datetime, timedelta

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import get_password_hash
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.auth_security import AuthSession
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.mfa_service import MfaService
from app.services.session_service import SessionService, hash_refresh_token


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


@pytest.mark.asyncio
async def test_owner_can_force_logout_team_session(client: AsyncClient, db: AsyncSession):
    owner = await _owner(db)
    student = User(
        email="forced-logout@example.com",
        password_hash=get_password_hash("studentpass1"),
        role="student",
    )
    db.add(student)
    await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": student.email, "password": "studentpass1"},
    )
    student_token = login.json()["access_token"]
    client.cookies.clear()
    student_headers = {"Authorization": f"Bearer {student_token}"}
    sessions = await client.get("/api/auth/sessions", headers=student_headers)
    session_id = sessions.json()[0]["id"]

    owner_token = AuthService.create_tokens(owner.id, owner.token_version).access_token
    response = await client.request(
        "DELETE",
        f"/api/admin/team/users/{student.id}/sessions/{session_id}",
        json={"reason": "Security incident investigation"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 204, response.text
    assert (await client.get("/api/auth/me", headers=student_headers)).status_code == 401


@pytest.mark.asyncio
async def test_privileged_role_promotion_revokes_existing_sessions(
    client: AsyncClient,
    db: AsyncSession,
):
    owner = await _owner(db)
    admin_role = Role(name="admin", description="Admin", is_system=True)
    target = User(
        email="promoted-admin@example.com",
        password_hash=get_password_hash("PromotedAdminPass1!"),
        role="student",
    )
    db.add_all([admin_role, target])
    await db.commit()

    target_login = await client.post(
        "/api/auth/login",
        json={"email": target.email, "password": "PromotedAdminPass1!"},
    )
    old_access_token = target_login.json()["access_token"]
    old_token_version = target.token_version
    client.cookies.clear()

    owner_token = AuthService.create_tokens(owner.id, owner.token_version).access_token
    promoted = await client.put(
        f"/api/admin/team/users/{target.id}/roles",
        json={"roles": ["admin"], "reason": "Operations team promotion"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert promoted.status_code == 200, promoted.text

    await db.refresh(target)
    assert target.token_version == old_token_version + 1
    rejected_session = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"},
    )
    assert rejected_session.status_code == 401
    setup_required = await client.post(
        "/api/auth/login",
        json={"email": target.email, "password": "PromotedAdminPass1!"},
    )
    assert setup_required.status_code == 403
    assert setup_required.json()["detail"]["code"] == "mfa_setup_required"


@pytest.mark.asyncio
async def test_sessionless_refresh_is_rejected_for_mfa_required_user(
    client: AsyncClient,
    db: AsyncSession,
):
    owner = await _owner(db)
    legacy_refresh = AuthService.create_tokens(
        owner.id,
        owner.token_version,
    ).refresh_token

    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": legacy_refresh},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_backup_code_cannot_be_consumed_concurrently(db: AsyncSession):
    owner = await _owner(db)
    credential, secret, _ = await MfaService.get_or_create_setup(db, owner)
    backup_codes = MfaService.enable(credential, pyotp.TOTP(secret).now())
    assert backup_codes
    backup_code = backup_codes[0]
    await db.commit()

    sessions = async_sessionmaker(bind=db.bind, class_=AsyncSession, expire_on_commit=False)
    first_locked = asyncio.Event()
    release_first = asyncio.Event()

    async def consume(*, hold_lock: bool) -> bool:
        async with sessions() as worker_db:
            locked = await MfaService.get_credential(
                worker_db,
                owner.id,
                for_update=True,
            )
            assert locked is not None
            if hold_lock:
                first_locked.set()
                await release_first.wait()
            valid = MfaService.verify(locked, backup_code)
            await worker_db.commit()
            return valid

    first_task = asyncio.create_task(consume(hold_lock=True))
    await first_locked.wait()
    second_task = asyncio.create_task(consume(hold_lock=False))
    _, pending = await asyncio.wait({second_task}, timeout=0.1)
    assert second_task in pending
    release_first.set()

    assert await first_task is True
    assert await second_task is False


@pytest.mark.asyncio
async def test_refresh_rotation_serializes_concurrent_reuse(db: AsyncSession):
    user = User(
        email="refresh-race@example.com",
        password_hash=get_password_hash("refreshpass1"),
        role="student",
    )
    db.add(user)
    await db.flush()
    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash="pending",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(auth_session)
    await db.flush()
    original = AuthService.create_tokens(
        user.id,
        user.token_version,
        auth_session.id,
    ).refresh_token
    auth_session.refresh_token_hash = hash_refresh_token(original)
    await db.commit()

    sessions = async_sessionmaker(bind=db.bind, class_=AsyncSession, expire_on_commit=False)
    first_locked = asyncio.Event()
    release_first = asyncio.Event()

    async def rotate(*, hold_lock: bool):
        async with sessions() as worker_db:
            current = await SessionService.get_active(
                worker_db,
                auth_session.id,
                user.id,
                for_update=True,
            )
            assert current is not None
            if hold_lock:
                first_locked.set()
                await release_first.wait()
            tokens = await SessionService.rotate(worker_db, current, user, original)
            await worker_db.commit()
            return tokens

    first_task = asyncio.create_task(rotate(hold_lock=True))
    await first_locked.wait()
    second_task = asyncio.create_task(rotate(hold_lock=False))
    _, pending = await asyncio.wait({second_task}, timeout=0.1)
    assert second_task in pending
    release_first.set()

    assert await first_task is not None
    assert await second_task is None
