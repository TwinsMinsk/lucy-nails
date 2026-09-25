"""Operational CRM endpoints for students, commerce, and delivery queues."""

import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import require_permission, user_has_permission
from app.core.security import (
    create_account_activation_token,
    get_password_hash,
)
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.crm import StudentNote, StudentTag, StudentTagAssignment
from app.models.entitlement import Entitlement
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.payment_event import PaymentEvent
from app.models.progress import Progress
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.user import User
from app.services.access_service import AccessService
from app.services.audit_service import append_audit_log
from app.services.outbox_service import enqueue_outbox_message
from app.services.runtime_settings_service import RuntimeSettingsService


router = APIRouter()


def _mask_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator:
        return "***"
    return f"{local[:1]}***@{domain}"


def _mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(character for character in value if character.isdigit())
    return f"***{digits[-4:]}" if digits else "***"


class DashboardResponse(BaseModel):
    total_students: int
    active_entitlements: int
    gross_revenue_kopecks: int
    refunded_kopecks: int
    net_revenue_kopecks: int
    pending_orders: int
    payment_errors: int
    notification_dead_letters: int
    expiring_entitlements_7d: int


class SystemStatusResponse(BaseModel):
    checkout_enabled: bool
    environment: str
    integrations: dict[str, bool]
    outbox_pending: int
    outbox_dead_letter: int
    last_payment_event_at: datetime | None


class StudentListItem(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    phone: str | None
    role: str
    created_at: datetime
    active_entitlements: int


class StudentPage(BaseModel):
    items: list[StudentListItem]
    total: int
    limit: int
    offset: int


class StudentPurchase(BaseModel):
    id: UUID
    course_title: str
    tariff: str
    amount_kopecks: int
    payment_status: str
    payment_id: str | None
    paid_at: datetime | None
    expires_at: datetime


class StudentEntitlement(BaseModel):
    id: UUID
    course_id: UUID
    course_title: str
    source: str
    tariff: str
    status: str
    starts_at: datetime
    expires_at: datetime
    reason: str | None
    revoked_at: datetime | None


class StudentCertificate(BaseModel):
    id: UUID
    course_id: UUID
    certificate_number: str
    student_name: str
    issued_at: datetime


class StudentNoteResponse(BaseModel):
    id: UUID
    author_id: UUID
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class StudentLessonProgress(BaseModel):
    course_id: UUID
    course_title: str
    module_title: str
    module_order: int
    lesson_id: UUID
    lesson_title: str
    lesson_order: int
    is_completed: bool
    watched_seconds: int | None
    updated_at: datetime | None


class StudentDetail(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    phone: str | None
    telegram_id: int | None
    telegram_username: str | None
    role: str
    created_at: datetime
    completed_lessons: int
    tracked_lessons: int
    last_activity_at: datetime | None
    purchases: list[StudentPurchase]
    entitlements: list[StudentEntitlement]
    certificates: list[StudentCertificate]
    notes: list[StudentNoteResponse]
    tags: list[str]
    lesson_progress: list[StudentLessonProgress]


class StudentCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    course_id: UUID
    access_days: int = Field(default=settings.COURSE_ACCESS_DAYS, ge=1, le=3650)
    reason: str = Field(..., min_length=5, max_length=1000)


class StudentCreateResponse(BaseModel):
    user_id: UUID
    user_created: bool
    entitlement_id: UUID
    expires_at: datetime


class LoginLinkResponse(BaseModel):
    message: str
    notification_id: UUID


class StudentNoteCreate(BaseModel):
    body: str = Field(..., min_length=2, max_length=5000)


class StudentTagsUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)
    reason: str = Field(..., min_length=5, max_length=1000)


class OrderListItem(BaseModel):
    id: UUID
    customer_email: str
    customer_phone: str | None
    course_id: UUID
    course_title: str
    tariff: str
    amount_kopecks: int
    currency: str
    access_days: int
    status: str
    purchase_id: UUID | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EntitlementListItem(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str
    course_id: UUID
    course_title: str
    source: str
    tariff: str
    status: str
    starts_at: datetime
    expires_at: datetime
    reason: str | None
    revoked_at: datetime | None


class EntitlementPage(BaseModel):
    items: list[EntitlementListItem]
    total: int
    limit: int
    offset: int


class OrderPage(BaseModel):
    items: list[OrderListItem]
    total: int
    limit: int
    offset: int


class NotificationItem(BaseModel):
    id: UUID
    kind: str
    channel: str
    recipient: str
    status: str
    attempts: int
    max_attempts: int
    next_attempt_at: datetime
    sent_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationPage(BaseModel):
    items: list[NotificationItem]
    total: int
    limit: int
    offset: int


class RetryRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000)


class PaymentEventItem(BaseModel):
    id: UUID
    external_event_id: str | None
    order_reference: str | None
    order_id: UUID | None
    purchase_id: UUID | None
    event_type: str
    processing_status: str
    amount_kopecks: int | None
    currency: str | None
    error_code: str | None
    error_detail: str | None
    received_at: datetime
    processed_at: datetime | None

    class Config:
        from_attributes = True


class PaymentEventPage(BaseModel):
    items: list[PaymentEventItem]
    total: int
    limit: int
    offset: int


class ReconciliationResponse(BaseModel):
    stale_pending_orders: int
    processed_payment_errors: int
    successful_purchases_without_active_entitlement: int
    dead_letter_notifications: int


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    now = datetime.utcnow()
    week = now + timedelta(days=7)
    total_students = await db.scalar(select(func.count(User.id)).where(User.role == "student"))
    active_entitlements = await db.scalar(
        select(func.count(Entitlement.id)).where(
            Entitlement.status == "active", Entitlement.expires_at > now
        )
    )
    gross = await db.scalar(
        select(func.coalesce(func.sum(Purchase.amount_kopecks), 0)).where(
            Purchase.payment_status == "success"
        )
    )
    refunded = await db.scalar(
        select(func.coalesce(func.sum(RefundRequest.amount_kopecks), 0)).where(
            RefundRequest.status == "processed"
        )
    )
    pending_orders = await db.scalar(select(func.count(Order.id)).where(Order.status == "pending"))
    payment_errors = await db.scalar(
        select(func.count(PaymentEvent.id)).where(
            PaymentEvent.processing_status == "rejected"
        )
    )
    dead_letters = await db.scalar(
        select(func.count(OutboxMessage.id)).where(OutboxMessage.status == "dead_letter")
    )
    expiring = await db.scalar(
        select(func.count(Entitlement.id)).where(
            Entitlement.status == "active",
            Entitlement.expires_at > now,
            Entitlement.expires_at <= week,
        )
    )
    return DashboardResponse(
        total_students=int(total_students or 0),
        active_entitlements=int(active_entitlements or 0),
        gross_revenue_kopecks=int(gross or 0),
        refunded_kopecks=int(refunded or 0),
        net_revenue_kopecks=int(gross or 0) - int(refunded or 0),
        pending_orders=int(pending_orders or 0),
        payment_errors=int(payment_errors or 0),
        notification_dead_letters=int(dead_letters or 0),
        expiring_entitlements_7d=int(expiring or 0),
    )


@router.get("/system/status", response_model=SystemStatusResponse)
async def system_status(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("audit.read")),
):
    pending = await db.scalar(
        select(func.count(OutboxMessage.id)).where(OutboxMessage.status == "pending")
    )
    dead = await db.scalar(
        select(func.count(OutboxMessage.id)).where(OutboxMessage.status == "dead_letter")
    )
    last_payment = await db.scalar(select(func.max(PaymentEvent.received_at)))
    return SystemStatusResponse(
        checkout_enabled=await RuntimeSettingsService.checkout_enabled(db),
        environment=settings.ENVIRONMENT,
        integrations={
            "prodamus": bool(settings.PRODAMUS_URL and settings.PRODAMUS_SECRET_KEY),
            "kinescope": bool(settings.KINESCOPE_API_KEY),
            "email": bool(
                settings.RESEND_API_KEY or (settings.SMTP_USER and settings.SMTP_PASSWORD)
            ),
            "telegram": bool(settings.TELEGRAM_BOT_TOKEN),
            "redis": bool(settings.REDIS_URL),
        },
        outbox_pending=int(pending or 0),
        outbox_dead_letter=int(dead or 0),
        last_payment_event_at=last_payment,
    )


@router.get("/students", response_model=StudentPage)
async def list_students(
    search: str | None = Query(default=None, max_length=255),
    active_access: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("users.read")),
):
    now = datetime.utcnow()
    active_count = (
        select(func.count(Entitlement.id))
        .where(
            Entitlement.user_id == User.id,
            Entitlement.status == "active",
            Entitlement.expires_at > now,
        )
        .correlate(User)
        .scalar_subquery()
    )
    conditions = [User.role == "student"]
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )
    if active_access is True:
        conditions.append(active_count > 0)
    elif active_access is False:
        conditions.append(active_count == 0)
    total = await db.scalar(select(func.count(User.id)).where(*conditions))
    result = await db.execute(
        select(User, active_count.label("active_entitlements"))
        .where(*conditions)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = [
        StudentListItem(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role,
            created_at=user.created_at,
            active_entitlements=int(count or 0),
        )
        for user, count in result.all()
    ]
    return StudentPage(items=items, total=int(total or 0), limit=limit, offset=offset)


@router.get("/students/{user_id}", response_model=StudentDetail)
async def student_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("users.read")),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    purchase_rows = (
        await db.execute(
            select(Purchase, Course.title)
            .join(Course, Course.id == Purchase.course_id)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.created_at.desc())
        )
    ).all()
    entitlement_rows = (
        await db.execute(
            select(Entitlement, Course.title)
            .join(Course, Course.id == Entitlement.course_id)
            .where(Entitlement.user_id == user_id)
            .order_by(Entitlement.created_at.desc())
        )
    ).all()
    progress = (
        await db.execute(select(Progress).where(Progress.user_id == user_id))
    ).scalars().all()
    access_course_ids = {item.course_id for item, _ in entitlement_rows} | {
        item.course_id for item, _ in purchase_rows if item.payment_status == "success"
    }
    lesson_rows = []
    if access_course_ids:
        # Published modules only, matching ProgressService completion and certificates.
        lesson_rows = (
            await db.execute(
                select(
                    Course.id.label("course_id"),
                    Course.title.label("course_title"),
                    Module.title.label("module_title"),
                    Module.order_index.label("module_order"),
                    Lesson.id.label("lesson_id"),
                    Lesson.title.label("lesson_title"),
                    Lesson.order_index.label("lesson_order"),
                    func.coalesce(Progress.is_completed, False).label("is_completed"),
                    Progress.watched_seconds.label("watched_seconds"),
                    Progress.updated_at.label("updated_at"),
                )
                .join(Module, Module.course_id == Course.id)
                .join(Lesson, Lesson.module_id == Module.id)
                .outerjoin(
                    Progress,
                    and_(Progress.lesson_id == Lesson.id, Progress.user_id == user_id),
                )
                .where(
                    Course.id.in_(list(access_course_ids)),
                    Module.is_published.is_(True),
                )
                .order_by(
                    Course.title,
                    Course.id,
                    Module.order_index,
                    Module.created_at,
                    Lesson.order_index,
                    Lesson.created_at,
                )
            )
        ).all()
    certificates = (
        await db.execute(
            select(Certificate)
            .where(Certificate.user_id == user_id)
            .order_by(Certificate.issued_at.desc())
        )
    ).scalars().all()
    notes = (
        await db.execute(
            select(StudentNote)
            .where(StudentNote.user_id == user_id)
            .order_by(StudentNote.created_at.desc())
        )
    ).scalars().all()
    tags = (
        await db.execute(
            select(StudentTag.name)
            .join(StudentTagAssignment, StudentTagAssignment.tag_id == StudentTag.id)
            .where(StudentTagAssignment.user_id == user_id)
            .order_by(StudentTag.name)
        )
    ).scalars().all()
    return StudentDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
        role=user.role,
        created_at=user.created_at,
        completed_lessons=sum(1 for item in progress if item.is_completed),
        tracked_lessons=len(progress),
        last_activity_at=max((item.updated_at for item in progress), default=None),
        purchases=[
            StudentPurchase(
                id=item.id,
                course_title=title,
                tariff=item.tariff,
                amount_kopecks=item.amount_kopecks,
                payment_status=item.payment_status,
                payment_id=item.payment_id,
                paid_at=item.paid_at,
                expires_at=item.expires_at,
            )
            for item, title in purchase_rows
        ],
        entitlements=[
            StudentEntitlement(
                id=item.id,
                course_id=item.course_id,
                course_title=title,
                source=item.source,
                tariff=item.tariff,
                status=item.status,
                starts_at=item.starts_at,
                expires_at=item.expires_at,
                reason=item.reason,
                revoked_at=item.revoked_at,
            )
            for item, title in entitlement_rows
        ],
        certificates=[
            StudentCertificate(
                id=item.id,
                course_id=item.course_id,
                certificate_number=item.certificate_number,
                student_name=item.student_name,
                issued_at=item.issued_at,
            )
            for item in certificates
        ],
        notes=list(notes),
        tags=list(tags),
        lesson_progress=[StudentLessonProgress(**row._mapping) for row in lesson_rows],
    )


@router.post(
    "/students",
    response_model=StudentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_student_with_access(
    data: StudentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("access.manage")),
):
    """Create (or reuse) a student account, grant manual access and email them."""
    course = await db.get(Course, data.course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    email = data.email.strip().lower()
    user = await db.scalar(select(User).where(func.lower(User.email) == email).limit(1))
    user_created = user is None
    if user is None:
        user = User(
            email=email,
            # Unusable until the student sets a password via the activation link.
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            full_name=data.full_name or None,
            phone=data.phone or None,
            role="student",
        )
        db.add(user)
        try:
            await db.flush()
        except IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail="Пользователь с таким email уже существует — повторите запрос",
            ) from exc

    entitlement = await AccessService.grant_manual_access(
        db,
        user_id=user.id,
        course_id=course.id,
        tariff="self",
        access_days=data.access_days,
        granted_by_id=admin.id,
        reason=data.reason,
    )
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    if user_created:
        activation_token = create_account_activation_token(user.id, user.token_version)
        notification_kind = "account_activation"
        enqueue_outbox_message(
            db,
            kind=notification_kind,
            recipient=user.email,
            payload={
                "activation_url": f"{frontend_url}/auth/activate?token={activation_token}",
                "course_title": course.title,
                "expires_at": entitlement.expires_at.isoformat(),
            },
            dedupe_key=f"admin-student:{entitlement.id}:activation",
        )
        append_audit_log(
            db,
            actor_user_id=admin.id,
            action="student.create",
            object_type="user",
            object_id=str(user.id),
            reason=data.reason,
            correlation_id=request.state.correlation_id,
            new_value={"role": "student", "course_id": str(course.id)},
        )
    else:
        notification_kind = "access_granted"
        enqueue_outbox_message(
            db,
            kind=notification_kind,
            recipient=user.email,
            payload={
                "login_url": f"{frontend_url}/auth/login",
                "course_title": course.title,
                "expires_at": entitlement.expires_at.isoformat(),
            },
            dedupe_key=f"admin-student:{entitlement.id}:access",
        )
    append_audit_log(
        db,
        actor_user_id=admin.id,
        action="entitlement.grant",
        object_type="entitlement",
        object_id=str(entitlement.id),
        reason=data.reason,
        correlation_id=request.state.correlation_id,
        new_value={
            "user_id": str(user.id),
            "course_id": str(course.id),
            "tariff": "self",
            "access_days": data.access_days,
            "expires_at": entitlement.expires_at.isoformat(),
            "notification": notification_kind,
        },
    )
    await db.commit()
    return StudentCreateResponse(
        user_id=user.id,
        user_created=user_created,
        entitlement_id=entitlement.id,
        expires_at=entitlement.expires_at,
    )


@router.post("/students/{user_id}/send-login-link", response_model=LoginLinkResponse)
async def send_student_login_link(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("users.manage")),
):
    """Email the student a one-time link to set a password and sign in."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Activation tokens live for hours (not minutes), so a student can open the
    # support email later; /auth/activate sets the password for any account.
    token = create_account_activation_token(user.id, user.token_version)
    message = enqueue_outbox_message(
        db,
        kind="login_link",
        recipient=user.email,
        payload={
            "login_url": (
                f"{settings.FRONTEND_URL.rstrip('/')}/auth/activate?token={token}"
            ),
        },
        # Every admin request is a deliberate resend, so it must never be deduplicated.
        dedupe_key=f"admin-login-link:{user.id}:{uuid4().hex}",
    )
    await db.flush()
    append_audit_log(
        db,
        actor_user_id=admin.id,
        action="student.login_link.send",
        object_type="user",
        object_id=str(user.id),
        reason="Admin sent a login link",
        correlation_id=request.state.correlation_id,
        new_value={"outbox_message_id": str(message.id)},
    )
    await db.commit()
    return LoginLinkResponse(message="Login link queued", notification_id=message.id)


@router.post(
    "/students/{user_id}/notes",
    response_model=StudentNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_student_note(
    user_id: UUID,
    data: StudentNoteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("users.manage")),
):
    if await db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    note = StudentNote(user_id=user_id, author_id=admin.id, body=data.body.strip())
    db.add(note)
    await db.flush()
    append_audit_log(
        db,
        actor_user_id=admin.id,
        action="student.note.create",
        object_type="student_note",
        object_id=str(note.id),
        new_value={"user_id": str(user_id)},
        reason="CRM note created",
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    await db.refresh(note)
    return note


@router.put("/students/{user_id}/tags", response_model=list[str])
async def update_student_tags(
    user_id: UUID,
    data: StudentTagsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("users.manage")),
):
    if await db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    normalized = sorted({item.strip().lower() for item in data.tags if item.strip()})
    if any(len(item) > 50 for item in normalized):
        raise HTTPException(status_code=422, detail="Tag must be at most 50 characters")
    old_tags = list(
        (
            await db.execute(
                select(StudentTag.name)
                .join(StudentTagAssignment, StudentTagAssignment.tag_id == StudentTag.id)
                .where(StudentTagAssignment.user_id == user_id)
                .order_by(StudentTag.name)
            )
        ).scalars().all()
    )
    existing = {
        item.name: item
        for item in (
            await db.execute(select(StudentTag).where(StudentTag.name.in_(normalized)))
        ).scalars().all()
    }
    await db.execute(
        delete(StudentTagAssignment).where(StudentTagAssignment.user_id == user_id)
    )
    for name in normalized:
        tag = existing.get(name)
        if tag is None:
            tag = StudentTag(name=name)
            db.add(tag)
            await db.flush()
        db.add(
            StudentTagAssignment(
                user_id=user_id,
                tag_id=tag.id,
                assigned_by_id=admin.id,
            )
        )
    append_audit_log(
        db,
        actor_user_id=admin.id,
        action="student.tags.update",
        object_type="user",
        object_id=str(user_id),
        old_value={"tags": old_tags},
        new_value={"tags": normalized},
        reason=data.reason,
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    return normalized


@router.get("/entitlements", response_model=EntitlementPage)
async def list_entitlements(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    expiring_days: int | None = Query(default=None, ge=1, le=3650),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("users.read")),
):
    conditions = []
    if search:
        conditions.append(User.email.ilike(f"%{search.strip()}%"))
    if status_filter:
        conditions.append(Entitlement.status == status_filter)
    if expiring_days:
        now = datetime.utcnow()
        conditions.extend(
            [Entitlement.expires_at > now, Entitlement.expires_at <= now + timedelta(days=expiring_days)]
        )
    total = await db.scalar(
        select(func.count(Entitlement.id))
        .join(User, User.id == Entitlement.user_id)
        .where(*conditions)
    )
    rows = (
        await db.execute(
            select(Entitlement, User.email, Course.title)
            .join(User, User.id == Entitlement.user_id)
            .join(Course, Course.id == Entitlement.course_id)
            .where(*conditions)
            .order_by(Entitlement.expires_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return EntitlementPage(
        items=[
            EntitlementListItem(
                id=item.id,
                user_id=item.user_id,
                user_email=email,
                course_id=item.course_id,
                course_title=course_title,
                source=item.source,
                tariff=item.tariff,
                status=item.status,
                starts_at=item.starts_at,
                expires_at=item.expires_at,
                reason=item.reason,
                revoked_at=item.revoked_at,
            )
            for item, email, course_title in rows
        ],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get("/orders", response_model=OrderPage)
async def list_orders(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("commerce.read")),
):
    can_read_pii = await user_has_permission(db, admin, "pii.read")
    conditions = []
    if search:
        conditions.append(Order.customer_email.ilike(f"%{search.strip()}%"))
    if status_filter:
        conditions.append(Order.status == status_filter)
    total = await db.scalar(select(func.count(Order.id)).where(*conditions))
    rows = (
        await db.execute(
            select(Order, Purchase.id)
            .outerjoin(Purchase, Purchase.order_id == Order.id)
            .where(*conditions)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return OrderPage(
        items=[
            OrderListItem(
                id=order.id,
                customer_email=(
                    order.customer_email
                    if can_read_pii
                    else _mask_email(order.customer_email)
                ),
                customer_phone=(
                    order.customer_phone
                    if can_read_pii
                    else _mask_phone(order.customer_phone)
                ),
                course_id=order.course_id,
                course_title=order.course_title,
                tariff=order.tariff,
                amount_kopecks=order.amount_kopecks,
                currency=order.currency,
                access_days=order.access_days,
                status=order.status,
                purchase_id=purchase_id,
                paid_at=order.paid_at,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )
            for order, purchase_id in rows
        ],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get("/notifications", response_model=NotificationPage)
async def list_notifications(
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    channel: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("notifications.manage")),
):
    conditions = []
    if status_filter:
        conditions.append(OutboxMessage.status == status_filter)
    if channel:
        conditions.append(OutboxMessage.channel == channel)
    total = await db.scalar(select(func.count(OutboxMessage.id)).where(*conditions))
    items = (
        await db.execute(
            select(OutboxMessage)
            .where(*conditions)
            .order_by(OutboxMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return NotificationPage(items=list(items), total=int(total or 0), limit=limit, offset=offset)


@router.post("/notifications/{message_id}/retry", response_model=NotificationItem)
async def retry_notification(
    message_id: UUID,
    data: RetryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("notifications.manage")),
):
    message = await db.get(OutboxMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    old_value = {"status": message.status, "attempts": message.attempts}
    message.status = "pending"
    message.attempts = 0
    message.next_attempt_at = datetime.utcnow()
    message.locked_at = None
    message.last_error = None
    append_audit_log(
        db,
        actor_user_id=admin.id,
        action="notification.retry",
        object_type="outbox_message",
        object_id=str(message.id),
        old_value=old_value,
        new_value={"status": "pending", "attempts": 0},
        reason=data.reason,
        correlation_id=request.state.correlation_id,
    )
    await db.commit()
    await db.refresh(message)
    return message


@router.get("/payment-events", response_model=PaymentEventPage)
async def list_payment_events(
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("commerce.read")),
):
    conditions = [PaymentEvent.processing_status == status_filter] if status_filter else []
    total = await db.scalar(select(func.count(PaymentEvent.id)).where(*conditions))
    items = (
        await db.execute(
            select(PaymentEvent)
            .where(*conditions)
            .order_by(PaymentEvent.received_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return PaymentEventPage(items=list(items), total=int(total or 0), limit=limit, offset=offset)


@router.get("/reconciliation", response_model=ReconciliationResponse)
async def reconciliation(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("commerce.read")),
):
    now = datetime.utcnow()
    stale = await db.scalar(
        select(func.count(Order.id)).where(
            Order.status == "pending", Order.created_at < now - timedelta(hours=2)
        )
    )
    payment_errors = await db.scalar(
        select(func.count(PaymentEvent.id)).where(
            PaymentEvent.processing_status == "rejected"
        )
    )
    processed_refund_total = (
        select(func.coalesce(func.sum(RefundRequest.amount_kopecks), 0))
        .where(
            RefundRequest.purchase_id == Purchase.id,
            RefundRequest.status == "processed",
        )
        .correlate(Purchase)
        .scalar_subquery()
    )
    without_access = await db.scalar(
        select(func.count(Purchase.id)).where(
            Purchase.payment_status == "success",
            Purchase.expires_at > now,
            processed_refund_total < Purchase.amount_kopecks,
            ~select(Entitlement.id)
            .where(
                Entitlement.source_purchase_id == Purchase.id,
            )
            .exists(),
        )
    )
    dead_letters = await db.scalar(
        select(func.count(OutboxMessage.id)).where(OutboxMessage.status == "dead_letter")
    )
    return ReconciliationResponse(
        stale_pending_orders=int(stale or 0),
        processed_payment_errors=int(payment_errors or 0),
        successful_purchases_without_active_entitlement=int(without_access or 0),
        dead_letter_notifications=int(dead_letters or 0),
    )
