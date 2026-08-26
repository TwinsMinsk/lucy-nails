"""Administrative certificate registry and lifecycle actions."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.outbox import OutboxMessage
from app.models.user import User
from app.services.audit_service import append_audit_log
from app.services.outbox_service import enqueue_outbox_message


router = APIRouter()


class CertificateAdminItem(BaseModel):
    id: UUID
    user_id: UUID
    student_email: str
    course_id: UUID
    course_title: str
    certificate_number: str
    student_name: str
    pdf_url: str | None
    png_url: str | None
    status: str
    revoke_reason: str | None
    revoked_at: datetime | None
    issued_at: datetime


class CertificatePage(BaseModel):
    items: list[CertificateAdminItem]
    total: int
    limit: int
    offset: int


class CertificateAction(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000)


async def _certificate_item(db: AsyncSession, certificate_id: UUID) -> CertificateAdminItem:
    row = (
        await db.execute(
            select(Certificate, User.email, Course.title)
            .join(User, User.id == Certificate.user_id)
            .join(Course, Course.id == Certificate.course_id)
            .where(Certificate.id == certificate_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    certificate, email, course_title = row
    return CertificateAdminItem(
        id=certificate.id,
        user_id=certificate.user_id,
        student_email=email,
        course_id=certificate.course_id,
        course_title=course_title,
        certificate_number=certificate.certificate_number,
        student_name=certificate.student_name,
        pdf_url=certificate.pdf_url,
        png_url=certificate.png_url,
        status=certificate.status,
        revoke_reason=certificate.revoke_reason,
        revoked_at=certificate.revoked_at,
        issued_at=certificate.issued_at,
    )


@router.get("/certificates", response_model=CertificatePage)
async def list_certificates(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status", max_length=20),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("certificates.manage")),
):
    conditions = []
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.email.ilike(pattern),
                Certificate.student_name.ilike(pattern),
                Certificate.certificate_number.ilike(pattern),
            )
        )
    if status_filter:
        conditions.append(Certificate.status == status_filter)
    total = await db.scalar(
        select(func.count(Certificate.id))
        .join(User, User.id == Certificate.user_id)
        .where(*conditions)
    )
    rows = (
        await db.execute(
            select(Certificate, User.email, Course.title)
            .join(User, User.id == Certificate.user_id)
            .join(Course, Course.id == Certificate.course_id)
            .where(*conditions)
            .order_by(Certificate.issued_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return CertificatePage(
        items=[
            CertificateAdminItem(
                id=certificate.id,
                user_id=certificate.user_id,
                student_email=email,
                course_id=certificate.course_id,
                course_title=course_title,
                certificate_number=certificate.certificate_number,
                student_name=certificate.student_name,
                pdf_url=certificate.pdf_url,
                png_url=certificate.png_url,
                status=certificate.status,
                revoke_reason=certificate.revoke_reason,
                revoked_at=certificate.revoked_at,
                issued_at=certificate.issued_at,
            )
            for certificate, email, course_title in rows
        ],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.post("/certificates/{certificate_id}/reissue", response_model=CertificateAdminItem)
async def reissue_certificate(
    certificate_id: UUID,
    data: CertificateAction,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("certificates.manage")),
):
    certificate = await db.get(Certificate, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if certificate.status != "active":
        raise HTTPException(status_code=409, detail="Revoked certificate cannot be reissued")
    item = await _certificate_item(db, certificate_id)
    dedupe_key = f"certificate-reissue:{certificate.id}:{datetime.utcnow():%Y%m%d%H}"
    existing = await db.scalar(
        select(OutboxMessage).where(OutboxMessage.dedupe_key == dedupe_key)
    )
    if existing is None:
        enqueue_outbox_message(
            db,
            kind="certificate_reissue",
            recipient=item.student_email,
            payload={
                "student_name": item.student_name,
                "course_title": item.course_title,
                "certificate_number": item.certificate_number,
                "verify_url": f"{settings.FRONTEND_URL.rstrip('/')}/certificate/{item.certificate_number}",
            },
            dedupe_key=dedupe_key,
        )
    append_audit_log(
        db,
        actor_user_id=admin.id,
        action="certificate.reissue",
        object_type="certificate",
        object_id=str(certificate.id),
        reason=data.reason,
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    return item


@router.post("/certificates/{certificate_id}/revoke", response_model=CertificateAdminItem)
async def revoke_certificate(
    certificate_id: UUID,
    data: CertificateAction,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("certificates.manage")),
):
    certificate = await db.get(Certificate, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    old_status = certificate.status
    certificate.status = "revoked"
    certificate.revoked_at = datetime.utcnow()
    certificate.revoked_by_id = admin.id
    certificate.revoke_reason = data.reason
    append_audit_log(
        db,
        actor_user_id=admin.id,
        action="certificate.revoke",
        object_type="certificate",
        object_id=str(certificate.id),
        old_value={"status": old_status},
        new_value={"status": "revoked"},
        reason=data.reason,
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    return await _certificate_item(db, certificate_id)
