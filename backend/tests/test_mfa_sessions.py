import asyncio
from datetime import datetime, timedelta

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import get_password_hash
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.auth_security import AuthSession
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.mfa_service import MfaService
from app.services.session_service import SessionService, hash_refresh_token
from conftest import mfa_headers


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

    # The confirmation consumed the current step; the next one is still in the window.
    login = await client.post(
        "/api/auth/login",
        json={**credentials, "mfa_code": pyotp.TOTP(secret).at(datetime.now(), 1)},
    )
    assert login.status_code == 200, login.text


async def _owner_with_totp(db: AsyncSession) -> tuple[User, str]:
    owner = await _owner(db)
    credential, secret, _ = await MfaService.get_or_create_setup(db, owner)
    credential.enabled_at = datetime.utcnow()
    await db.commit()
    return owner, secret


@pytest.mark.asyncio
async def test_totp_code_cannot_be_replayed(client: AsyncClient, db: AsyncSession):
    owner, secret = await _owner_with_totp(db)
    credentials = {"email": owner.email, "password": "StrongOwnerPass1!"}
    code = pyotp.TOTP(secret).now()

    first = await client.post("/api/auth/login", json={**credentials, "mfa_code": code})
    assert first.status_code == 200, first.text
    client.cookies.clear()
    replay = await client.post("/api/auth/login", json={**credentials, "mfa_code": code})
    assert replay.status_code == 401
    assert replay.json()["detail"]["code"] == "mfa_code_invalid"


@pytest.mark.asyncio
async def test_totp_code_for_an_earlier_step_is_refused(client: AsyncClient, db: AsyncSession):
    owner, secret = await _owner_with_totp(db)
    credentials = {"email": owner.email, "password": "StrongOwnerPass1!"}
    totp = pyotp.TOTP(secret)
    now = datetime.now()

    later = await client.post(
        "/api/auth/login", json={**credentials, "mfa_code": totp.at(now, 1)}
    )
    assert later.status_code == 200, later.text
    client.cookies.clear()
    earlier = await client.post(
        "/api/auth/login", json={**credentials, "mfa_code": totp.at(now, 0)}
    )
    assert earlier.status_code == 401
    credential = await MfaService.get_credential(db, owner.id)
    await db.refresh(credential)
    assert credential.last_totp_step == totp.timecode(now) + 1


@pytest.mark.asyncio
async def test_legacy_admin_without_rbac_must_setup_and_use_mfa(
    client: AsyncClient, db: AsyncSession
):
    legacy = User(
        email="legacy-admin@example.com",
        password_hash=get_password_hash("LegacyAdminPass1!"),
        role="admin",
    )
    db.add(legacy)
    await db.commit()
    credentials = {"email": legacy.email, "password": "LegacyAdminPass1!"}

    initial = await client.post("/api/auth/login", json=credentials)
    assert initial.status_code == 403, initial.text
    detail = initial.json()["detail"]
    assert detail["code"] == "mfa_setup_required"
    setup = await client.post("/api/auth/mfa/setup", json={"setup_token": detail["setup_token"]})
    assert setup.status_code == 200, setup.text
    confirm = await client.post(
        "/api/auth/mfa/confirm",
        json={"setup_token": detail["setup_token"], "code": pyotp.TOTP(setup.json()["secret"]).now()},
    )
    assert confirm.status_code == 200, confirm.text
    client.cookies.clear()

    missing_code = await client.post("/api/auth/login", json=credentials)
    assert missing_code.status_code == 401
    assert missing_code.json()["detail"]["code"] == "mfa_code_required"
    # The legacy fallback itself stays: with MFA the account keeps every permission.
    login = await client.post(
        "/api/auth/login",
        json={**credentials, "mfa_code": confirm.json()["backup_codes"][0]},
    )
    assert login.status_code == 200, login.text
    client.cookies.clear()
    capabilities = await client.get(
        "/api/admin/team/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert capabilities.json()["permissions"] == ["*"]


async def _pre_deploy_session(db: AsyncSession, user: User) -> tuple[AuthSession, str, str]:
    """A session issued before sessions recorded their MFA state (NULL)."""
    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash="pending",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(auth_session)
    await db.flush()
    tokens = AuthService.create_tokens(user.id, user.token_version, auth_session.id)
    auth_session.refresh_token_hash = hash_refresh_token(tokens.refresh_token)
    await db.commit()
    assert auth_session.mfa_verified is None
    return auth_session, tokens.access_token, tokens.refresh_token


@pytest.mark.asyncio
async def test_old_password_only_legacy_admin_session_is_refused(
    client: AsyncClient, db: AsyncSession
):
    legacy = User(email="legacy-old@example.com", password_hash="x", role="admin")
    db.add(legacy)
    await db.commit()
    auth_session, access, refresh = await _pre_deploy_session(db, legacy)

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 401
    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 401
    await db.refresh(auth_session)
    assert auth_session.revoked_at is not None


@pytest.mark.asyncio
async def test_old_session_of_owner_with_mfa_is_refused_until_a_fresh_mfa_login(
    client: AsyncClient, db: AsyncSession
):
    owner, secret = await _owner_with_totp(db)
    auth_session, access, refresh = await _pre_deploy_session(db, owner)

    # An enabled credential does not prove this old session passed MFA.
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 401
    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 401
    await db.refresh(auth_session)
    assert auth_session.revoked_at is not None

    login = await client.post(
        "/api/auth/login",
        json={"email": owner.email, "password": "StrongOwnerPass1!", "mfa_code": pyotp.TOTP(secret).now()},
    )
    assert login.status_code == 200, login.text
    client.cookies.clear()
    fresh = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )
    assert fresh.status_code == 200, fresh.text


@pytest.mark.asyncio
async def test_old_password_only_session_of_legacy_admin_with_credential_is_refused(
    client: AsyncClient, db: AsyncSession
):
    legacy = User(email="legacy-cred@example.com", password_hash="x", role="admin")
    db.add(legacy)
    await db.flush()
    credential, _, _ = await MfaService.get_or_create_setup(db, legacy)
    credential.enabled_at = datetime.utcnow()
    await db.commit()
    _, access, refresh = await _pre_deploy_session(db, legacy)

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 401
    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 401


@pytest.mark.asyncio
async def test_old_session_of_non_privileged_staff_is_served(client: AsyncClient, db: AsyncSession):
    analyst = User(email="analyst-old@example.com", password_hash="x", role="student")
    role = Role(name="analyst", description="Analyst", is_system=True)
    role.permissions = [Permission(name="analytics.read", description="analytics")]
    db.add_all([analyst, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=analyst.id, role_id=role.id))
    await db.commit()
    _, access, refresh = await _pre_deploy_session(db, analyst)

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200, me.text
    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200, refreshed.text


@pytest.mark.asyncio
async def test_old_student_session_is_untouched(client: AsyncClient, db: AsyncSession):
    student = User(email="old-student@example.com", password_hash="x", role="student")
    db.add(student)
    await db.commit()
    _, access, refresh = await _pre_deploy_session(db, student)

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200, me.text
    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200, refreshed.text


@pytest.mark.asyncio
async def test_session_issued_without_mfa_is_refused_once_account_requires_it(
    client: AsyncClient, db: AsyncSession
):
    user = User(
        email="later-admin@example.com",
        password_hash=get_password_hash("LaterAdminPass1!"),
        role="student",
    )
    db.add(user)
    await db.commit()
    login = await client.post(
        "/api/auth/login", json={"email": user.email, "password": "LaterAdminPass1!"}
    )
    access = login.json()["access_token"]
    client.cookies.clear()
    # Privilege granted outside the role API, which would revoke sessions itself.
    user.role = "admin"
    await db.commit()

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_owner_password_change_keeps_the_new_session_signed_in(
    client: AsyncClient, db: AsyncSession
):
    owner, secret = await _owner_with_totp(db)
    login = await client.post(
        "/api/auth/login",
        json={"email": owner.email, "password": "StrongOwnerPass1!", "mfa_code": pyotp.TOTP(secret).now()},
    )
    assert login.status_code == 200, login.text
    csrf = client.cookies.get("csrf_token")
    changed = await client.post(
        "/api/auth/change-password",
        json={"current_password": "StrongOwnerPass1!", "new_password": "NewOwnerPass2!"},
        headers={"x-csrf-token": csrf},
    )
    assert changed.status_code == 200, changed.text
    me = await client.get("/api/auth/me")
    assert me.status_code == 200, me.text


@pytest.mark.asyncio
async def test_mfa_requirement_by_account_kind(db: AsyncSession):
    owner = await _owner(db)
    legacy = User(email="legacy@example.com", password_hash="x", role="admin")
    student = User(email="student@example.com", password_hash="x", role="student")
    curator_role = Role(name="curator", description="Curator", is_system=True)
    # role="admin" with a non-privileged RBAC assignment is not a legacy admin.
    assigned = User(email="assigned@example.com", password_hash="x", role="admin")
    db.add_all([legacy, student, curator_role, assigned])
    await db.flush()
    db.add(UserRoleAssignment(user_id=assigned.id, role_id=curator_role.id))
    await db.commit()

    assert await MfaService.requires_mfa(db, owner.id) is True
    assert await MfaService.requires_mfa(db, legacy.id) is True
    assert await MfaService.requires_mfa(db, student.id) is False
    assert await MfaService.requires_mfa(db, assigned.id) is False


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

    owner_headers = await mfa_headers(client, db, owner, "StrongOwnerPass1!")
    response = await client.request(
        "DELETE",
        f"/api/admin/team/users/{student.id}/sessions/{session_id}",
        json={"reason": "Security incident investigation"},
        headers=owner_headers,
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
        email_verified_at=datetime.utcnow(),
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

    owner_headers = await mfa_headers(client, db, owner, "StrongOwnerPass1!")
    promoted = await client.put(
        f"/api/admin/team/users/{target.id}/roles",
        json={"roles": ["admin"], "reason": "Operations team promotion"},
        headers=owner_headers,
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
async def test_team_role_requires_confirmed_email(client: AsyncClient, db: AsyncSession):
    owner = await _owner(db)
    curator_role = Role(name="curator", description="Curator", is_system=True)
    squatter = User(
        email="staff-member@example.com",
        password_hash=get_password_hash("SquatterPass1!"),
        role="student",
    )
    db.add_all([curator_role, squatter])
    await db.commit()

    owner_headers = await mfa_headers(client, db, owner, "StrongOwnerPass1!")
    response = await client.put(
        f"/api/admin/team/users/{squatter.id}/roles",
        json={"roles": ["curator"], "reason": "New support curator"},
        headers=owner_headers,
    )

    assert response.status_code == 409
    assert "не подтверждена" in response.json()["detail"]
    assignment = await db.scalar(
        select(UserRoleAssignment.id).where(UserRoleAssignment.user_id == squatter.id)
    )
    assert assignment is None


@pytest.mark.asyncio
async def test_any_role_change_revokes_target_sessions(client: AsyncClient, db: AsyncSession):
    owner = await _owner(db)
    curator_role = Role(name="curator", description="Curator", is_system=True)
    target = User(
        email="curator@example.com",
        password_hash=get_password_hash("CuratorPass1!"),
        role="student",
        email_verified_at=datetime.utcnow(),
    )
    db.add_all([curator_role, target])
    await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": target.email, "password": "CuratorPass1!"},
    )
    old_access_token = login.json()["access_token"]
    client.cookies.clear()

    owner_headers = await mfa_headers(client, db, owner, "StrongOwnerPass1!")
    response = await client.put(
        f"/api/admin/team/users/{target.id}/roles",
        json={"roles": ["curator"], "reason": "New support curator"},
        headers=owner_headers,
    )

    assert response.status_code == 200, response.text
    await db.refresh(target)
    assert target.token_version == 1
    rejected = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {old_access_token}"}
    )
    assert rejected.status_code == 401


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


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["full_width_wrong", "arabic_indic", "full_width_valid"])
async def test_unicode_digit_codes_never_cause_a_server_error(
    client: AsyncClient, db: AsyncSession, kind: str
):
    owner, secret = await _owner_with_totp(db)
    valid = pyotp.TOTP(secret).now()
    full_width = "".join(chr(ord("０") + int(digit)) for digit in valid)
    codes = {
        "full_width_wrong": "１２３４５６" if valid != "123456" else "６５４３２１",
        "arabic_indic": "١٢٣٤٥٦",
        "full_width_valid": full_width,
    }

    response = await client.post(
        "/api/auth/login",
        json={"email": owner.email, "password": "StrongOwnerPass1!", "mfa_code": codes[kind]},
    )

    if kind == "full_width_valid":
        # NFKC turns full-width digits into the same code, as PyOTP always did.
        assert response.status_code == 200, response.text
    else:
        assert response.status_code == 401, response.text
        assert response.json()["detail"]["code"] == "mfa_code_invalid"


@pytest.mark.asyncio
async def test_privileged_access_token_without_session_is_refused(
    client: AsyncClient, db: AsyncSession
):
    owner = await _owner(db)
    sessionless = AuthService.create_tokens(owner.id, owner.token_version).access_token
    headers = {"Authorization": f"Bearer {sessionless}"}

    assert (await client.get("/api/auth/me", headers=headers)).status_code == 401
    changed = await client.post(
        "/api/auth/change-password",
        json={"current_password": "StrongOwnerPass1!", "new_password": "AnotherPass2!"},
        headers=headers,
    )
    assert changed.status_code == 401
    sessions = await db.scalar(select(AuthSession.id).where(AuthSession.user_id == owner.id))
    assert sessions is None


@pytest.mark.asyncio
async def test_student_access_token_without_session_is_still_served(
    client: AsyncClient, db: AsyncSession
):
    student = User(email="sessionless-student@example.com", password_hash="x", role="student")
    db.add(student)
    await db.commit()
    token = AuthService.create_tokens(student.id, student.token_version).access_token

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text


@pytest.mark.asyncio
async def test_password_change_session_inherits_mfa_state_and_never_upgrades_it(
    client: AsyncClient, db: AsyncSession
):
    student = User(
        email="inherit-student@example.com",
        password_hash=get_password_hash("StudentPass1!"),
        role="student",
    )
    db.add(student)
    await db.commit()
    login = await client.post(
        "/api/auth/login", json={"email": student.email, "password": "StudentPass1!"}
    )
    assert login.status_code == 200, login.text
    changed = await client.post(
        "/api/auth/change-password",
        json={"current_password": "StudentPass1!", "new_password": "StudentPass2!"},
        headers={"x-csrf-token": client.cookies.get("csrf_token")},
    )
    assert changed.status_code == 200, changed.text
    client.cookies.clear()

    owner, secret = await _owner_with_totp(db)
    owner_login = await client.post(
        "/api/auth/login",
        json={"email": owner.email, "password": "StrongOwnerPass1!", "mfa_code": pyotp.TOTP(secret).now()},
    )
    assert owner_login.status_code == 200, owner_login.text
    owner_changed = await client.post(
        "/api/auth/change-password",
        json={"current_password": "StrongOwnerPass1!", "new_password": "OwnerPass2!!"},
        headers={"x-csrf-token": client.cookies.get("csrf_token")},
    )
    assert owner_changed.status_code == 200, owner_changed.text

    db.expunge_all()
    active = {
        row.user_id: row.mfa_verified
        for row in (
            await db.execute(select(AuthSession).where(AuthSession.revoked_at.is_(None)))
        ).scalars()
    }
    assert active == {student.id: False, owner.id: True}
