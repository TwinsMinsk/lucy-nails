"""Team RBAC administration and append-only audit views."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.audit_log import AuditLog
from app.models.rbac import Role, UserRoleAssignment
from app.models.user import User
from app.services.audit_service import append_audit_log


router = APIRouter()


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str
    permissions: list[str]


class TeamRoleUpdate(BaseModel):
    roles: list[str] = Field(default_factory=list, max_length=5)
    reason: str = Field(..., min_length=5, max_length=1000)


class TeamRoleAssignmentResponse(BaseModel):
    user_id: UUID
    roles: list[str]


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
        owners_count = await db.scalar(
            select(func.count(UserRoleAssignment.id))
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(Role.name == "owner")
        )
        if int(owners_count or 0) <= 1:
            raise HTTPException(status_code=422, detail="Cannot remove the last owner")

    await db.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id == user_id))
    for role in roles:
        db.add(
            UserRoleAssignment(
                user_id=user_id,
                role_id=role.id,
                assigned_by_id=owner.id,
            )
        )
    target.role = "admin" if roles else "student"
    append_audit_log(
        db,
        actor_user_id=owner.id,
        action="team.roles.update",
        object_type="user",
        object_id=str(user_id),
        old_value={"roles": old_names},
        new_value={"roles": requested_names},
        reason=data.reason,
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    return TeamRoleAssignmentResponse(user_id=user_id, roles=requested_names)


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

