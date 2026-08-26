"""Team RBAC administration and append-only audit views."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.audit_log import AuditLog
from app.models.auth_security import AuthSession
from app.models.rbac import Role, UserRoleAssignment
from app.models.user import User
from app.services.audit_service import append_audit_log
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
    await db.execute(select(func.pg_advisory_xact_lock(761941013)))
    owners_count = await db.scalar(
        select(func.count(UserRoleAssignment.id))
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .where(Role.name == "owner")
    )
    if int(owners_count or 0) <= 1:
        raise HTTPException(status_code=422, detail="Cannot remove the last owner")


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
    target = await db.get(User, user_id)
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
    if "owner" in old_names and "owner" not in requested_names:
        await ensure_owner_removal_preserves_owner(db)

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
    privileged_assignment_changed = bool(
        (set(old_names) ^ set(requested_names)) & privileged_roles
    )
    target.role = (
        "admin"
        if any(role.name in privileged_roles for role in roles)
        else "student"
    )
    if privileged_assignment_changed:
        # Permissions are read from the database on each request. Invalidate
        # every pre-promotion token as well, otherwise an already authenticated
        # student could exercise owner/admin powers without an MFA login.
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
            "reauthentication_required": privileged_assignment_changed,
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
    return list(result.scalars().all())
