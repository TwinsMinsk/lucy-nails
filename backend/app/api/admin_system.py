"""Team RBAC administration and append-only audit views."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, user_has_permission
from app.models.audit_log import AuditLog
from app.models.auth_security import AuthSession
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from app.services.audit_service import append_audit_log, redact_audit_entry
from app.services.runtime_settings_service import RuntimeSettingsService
from app.services.session_service import SessionService


router = APIRouter()


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str
    permissions: list[str]


class TeamRoleUpdate(BaseModel):
    roles: list[str] = Field(default_factory=list, max_length=5)
    reason: str = Field(..., min_length=5, max_length=1000)


class ReasonRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000)


class TeamRoleAssignmentResponse(BaseModel):
    user_id: UUID
    roles: list[str]


class TeamUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    roles: list[str]
    mfa_enabled: bool
    active_sessions: int


class AuditLogResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    object_type: str
    object_id: str | None
    old_value: dict | None
    new_value: dict | None
    reason: str | None
    correlation_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class TeamCapabilitiesResponse(BaseModel):
    roles: list[str]
    permissions: list[str]


class CheckoutToggleRequest(BaseModel):
    enabled: bool
    reason: str = Field(..., min_length=5, max_length=1000)


async def ensure_owner_removal_preserves_owner(db: AsyncSession) -> None:
    """Serialize and validate removal of an owner assignment."""
    await db.execute(select(func.pg_advisory_xact_lock(ROLE_CHANGE_LOCK_KEY)))
    owners_count = await db.scalar(
        select(func.count(UserRoleAssignment.id))
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .where(Role.name == "owner")
    )
    if int(owners_count or 0) <= 1:
        raise HTTPException(status_code=422, detail="Cannot remove the last owner")


TEAM_MANAGEMENT_PERMISSION = "system.manage_roles"
ROLE_CHANGE_LOCK_KEY = 761941013


async def recheck_caller_under_role_lock(
    db: AsyncSession,
    request: Request,
    caller_id: UUID,
) -> User:
    """Re-read the caller after the role-change lock is held.

    Role changes are serialized by the lock, so a check made here sees every
    change committed while this request waited: the caller must still hold
    system.manage_roles, still have the token version and the session the
    request was authenticated with, and that session must still satisfy MFA.
    """
    from app.services.mfa_service import MfaService

    session_gone = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    caller = await db.scalar(
        select(User)
        .where(User.id == caller_id)
        .execution_options(populate_existing=True)
    )
    if caller is None or caller.token_version != getattr(
        request.state, "auth_token_version", None
    ):
        raise session_gone
    session_id = getattr(request.state, "auth_session_id", None)
    if session_id is not None:
        auth_session = await db.scalar(
            select(AuthSession)
            .where(
                AuthSession.id == session_id,
                AuthSession.user_id == caller.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.utcnow(),
            )
            .execution_options(populate_existing=True)
        )
        if auth_session is None or not await MfaService.session_satisfies_mfa(
            db, caller, auth_session
        ):
            raise session_gone
    elif await MfaService.requires_mfa(db, caller.id):
        raise session_gone
    if not await user_has_permission(db, caller, TEAM_MANAGEMENT_PERMISSION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {TEAM_MANAGEMENT_PERMISSION}",
        )
    return caller


async def ensure_team_keeps_a_manager(db: AsyncSession, target_id: UUID) -> None:
    """Refuse a change that leaves no account able to manage the team.

    Counts RBAC holders of system.manage_roles and legacy administrators
    (role="admin" without any assignment, who get every permission).
    Callers hold the role-change advisory lock.
    """
    holds_permission = (
        select(UserRoleAssignment.id)
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .join(Role.permissions)
        .where(
            UserRoleAssignment.user_id == User.id,
            Permission.name == TEAM_MANAGEMENT_PERMISSION,
        )
        .exists()
    )
    has_assignment = (
        select(UserRoleAssignment.id).where(UserRoleAssignment.user_id == User.id).exists()
    )
    other_managers = await db.scalar(
        select(func.count(User.id)).where(
            User.id != target_id,
            or_(holds_permission, and_(User.role == "admin", ~has_assignment)),
        )
    )
    if not other_managers:
        raise HTTPException(
            status_code=422,
            detail="Cannot remove team management from the last account that has it",
        )


class CheckoutToggleResponse(BaseModel):
    checkout_enabled: bool


@router.put("/system/checkout", response_model=CheckoutToggleResponse)
async def toggle_checkout(
    data: CheckoutToggleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_permission("system.manage_operations")),
):
    old_enabled = await RuntimeSettingsService.checkout_enabled(db)
    await RuntimeSettingsService.set_checkout_enabled(
        db, enabled=data.enabled, updated_by_id=operator.id
    )
    append_audit_log(
        db,
        actor_user_id=operator.id,
        action="system.checkout.toggle",
        object_type="runtime_setting",
        object_id=RuntimeSettingsService.CHECKOUT_KEY,
        old_value={"enabled": old_enabled},
        new_value={"enabled": data.enabled},
        reason=data.reason,
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    return CheckoutToggleResponse(checkout_enabled=data.enabled)


@router.get("/team/me", response_model=TeamCapabilitiesResponse)
async def team_capabilities(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Role)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .options(selectinload(Role.permissions))
        .where(UserRoleAssignment.user_id == current_user.id)
        .order_by(Role.name)
    )
    roles = list(result.scalars().unique().all())
    if not roles and current_user.role == "admin":
        return TeamCapabilitiesResponse(roles=["legacy_admin"], permissions=["*"])
    return TeamCapabilitiesResponse(
        roles=[role.name for role in roles],
        permissions=sorted(
            {permission.name for role in roles for permission in role.permissions}
        ),
    )


@router.get("/team/roles", response_model=list[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    owner: User = Depends(require_permission("system.manage_roles")),
):
    result = await db.execute(select(Role).options(selectinload(Role.permissions)).order_by(Role.name))
    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=sorted(permission.name for permission in role.permissions),
        )
        for role in result.scalars().all()
    ]


@router.get("/team/users", response_model=list[TeamUserResponse])
async def list_team_users(
    db: AsyncSession = Depends(get_db),
    owner: User = Depends(require_permission("system.manage_roles")),
):
    users = (
        await db.execute(
            select(User)
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .options(
                selectinload(User.role_assignments).selectinload(UserRoleAssignment.role),
                selectinload(User.mfa_credential),
            )
            .order_by(User.email)
        )
    ).scalars().unique().all()
    now = datetime.utcnow()
    session_counts = dict(
        (
            await db.execute(
                select(AuthSession.user_id, func.count(AuthSession.id))
                .where(AuthSession.revoked_at.is_(None), AuthSession.expires_at > now)
                .group_by(AuthSession.user_id)
            )
        ).all()
    )
    return [
        TeamUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            roles=sorted(item.role.name for item in user.role_assignments),
            mfa_enabled=bool(user.mfa_credential and user.mfa_credential.enabled_at),
            active_sessions=int(session_counts.get(user.id, 0)),
        )
        for user in users
    ]


@router.put("/team/users/{user_id}/roles", response_model=TeamRoleAssignmentResponse)
async def update_team_roles(
    user_id: UUID,
    data: TeamRoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    owner: User = Depends(require_permission("system.manage_roles")),
):
    # Serialize every role change: the last-manager checks below compare the
    # whole team, so two concurrent changes must not both pass them. The
    # advisory lock comes before any row lock: otherwise one change could hold
    # the lock and need KEY SHARE on the acting admin's row (assigned_by_id,
    # audit actor) while another holds that row FOR UPDATE and waits here.
    await db.execute(select(func.pg_advisory_xact_lock(ROLE_CHANGE_LOCK_KEY)))
    # The permission dependency ran before this request queued on the lock;
    # a role change committed meanwhile may have demoted the caller.
    owner = await recheck_caller_under_role_lock(db, request, owner.id)
    target = await db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    requested_names = sorted(set(data.roles))
    role_result = await db.execute(select(Role).where(Role.name.in_(requested_names)))
    roles = list(role_result.scalars().all())
    if len(roles) != len(requested_names):
        raise HTTPException(status_code=422, detail="Unknown role")

    old_result = await db.execute(
        select(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(UserRoleAssignment.user_id == user_id)
    )
    old_names = sorted(old_result.scalars().all())
    if set(requested_names) - set(old_names) and target.email_verified_at is None:
        # Registration stores the chosen password before the mailbox is proven,
        # so whoever registered this address may not be the staff member.
        # Confirming the address sets a new password and revokes sessions.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Почта этого аккаунта не подтверждена. Роль можно назначить "
                "после того, как сотрудник подтвердит адрес по ссылке из письма."
            ),
        )
    if "owner" in old_names and "owner" not in requested_names:
        await ensure_owner_removal_preserves_owner(db)
    keeps_team_management = bool(roles) and await db.scalar(
        select(Permission.id)
        .join(Permission.roles)
        .where(
            Role.id.in_([role.id for role in roles]),
            Permission.name == TEAM_MANAGEMENT_PERMISSION,
        )
        .limit(1)
    ) is not None
    if not keeps_team_management and await user_has_permission(
        db, target, TEAM_MANAGEMENT_PERMISSION
    ):
        await ensure_team_keeps_a_manager(db, target.id)

    await db.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id == user_id))
    for role in roles:
        db.add(
            UserRoleAssignment(
                user_id=user_id,
                role_id=role.id,
                assigned_by_id=owner.id,
            )
        )
    privileged_roles = {"owner", "admin"}
    old_legacy_role = target.role
    target.role = (
        "admin"
        if any(role.name in privileged_roles for role in roles)
        else "student"
    )
    # Dropping the legacy role="admin" also removes the all-permission fallback.
    assignment_changed = (
        set(old_names) != set(requested_names) or old_legacy_role != target.role
    )
    if assignment_changed:
        # Permissions are read from the database on each request. Invalidate
        # every token issued before the change, for every role, so rights are
        # only ever exercised from a login made after the assignment.
        target.token_version = (target.token_version or 0) + 1
        await SessionService.revoke_all(db, target.id)
    append_audit_log(
        db,
        actor_user_id=owner.id,
        action="team.roles.update",
        object_type="user",
        object_id=str(user_id),
        old_value={"roles": old_names},
        new_value={
            "roles": requested_names,
            "reauthentication_required": assignment_changed,
        },
        reason=data.reason,
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    return TeamRoleAssignmentResponse(user_id=user_id, roles=requested_names)


@router.delete(
    "/team/users/{user_id}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def force_logout_session(
    user_id: UUID,
    session_id: UUID,
    data: ReasonRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    owner: User = Depends(require_permission("system.manage_roles")),
):
    auth_session = await db.get(AuthSession, session_id)
    if auth_session is None or auth_session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    if auth_session.revoked_at is None:
        auth_session.revoked_at = datetime.utcnow()
    append_audit_log(
        db,
        actor_user_id=owner.id,
        action="auth.session.force_logout",
        object_type="auth_session",
        object_id=str(session_id),
        old_value={"revoked": False, "user_id": str(user_id)},
        new_value={"revoked": True},
        reason=data.reason,
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
    auditor: User = Depends(require_permission("audit.read")),
):
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    result = await db.execute(
        query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    entries = list(result.scalars().all())
    if await user_has_permission(db, auditor, "pii.read"):
        return entries
    return [redact_audit_entry(entry) for entry in entries]
