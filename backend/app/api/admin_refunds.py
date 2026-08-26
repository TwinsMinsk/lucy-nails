"""Administrative refund request workflow."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.refund import RefundRequest
from app.models.user import User
from app.services.refund_service import RefundError, RefundService


router = APIRouter()


class RefundCreate(BaseModel):
    purchase_id: UUID
    amount_kopecks: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5, max_length=2000)


class RefundUpdate(BaseModel):
    status: Literal["requested", "submitted", "processed", "rejected"]
    provider_reference: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


class RefundResponse(BaseModel):
    id: UUID
    purchase_id: UUID
    amount_kopecks: int
    reason: str
    status: str
    provider_reference: str | None
    note: str | None
    created_by_id: UUID
    processed_by_id: UUID | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _refund_http_error(error: RefundError) -> HTTPException:
    code = status.HTTP_404_NOT_FOUND if str(error) == "Purchase not found" else status.HTTP_422_UNPROCESSABLE_CONTENT
    return HTTPException(status_code=code, detail=str(error))


@router.get("/refunds", response_model=list[RefundResponse])
async def list_refunds(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("refunds.manage")),
):
    return await RefundService.list_refunds(db)


@router.post("/refunds", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def create_refund(
    data: RefundCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("refunds.manage")),
):
    try:
        refund = await RefundService.create_refund(
            db,
            purchase_id=data.purchase_id,
            amount_kopecks=data.amount_kopecks,
            reason=data.reason,
            created_by_id=admin.id,
        )
    except RefundError as error:
        raise _refund_http_error(error) from error
    await db.commit()
    await db.refresh(refund)
    return refund


@router.put("/refunds/{refund_id}", response_model=RefundResponse)
async def update_refund(
    refund_id: UUID,
    data: RefundUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("refunds.manage")),
):
    refund = await db.get(RefundRequest, refund_id)
    if refund is None:
        raise HTTPException(status_code=404, detail="Refund request not found")
    try:
        await RefundService.update_refund(
            db,
            refund,
            status=data.status,
            actor_id=admin.id,
            provider_reference=data.provider_reference,
            note=data.note,
        )
    except RefundError as error:
        raise _refund_http_error(error) from error
    await db.commit()
    await db.refresh(refund)
    return refund
