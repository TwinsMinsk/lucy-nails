"""Operational CRM endpoints for students, commerce, and delivery queues."""

import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import String, and_, case, cast, delete, func, literal, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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
from app.models.purchase import Purchase, paid_financial_filter
from app.models.rbac import UserRoleAssignment, student_account_filter
from app.models.refund import RefundRequest
from app.models.user import User
from app.services.access_service import AccessService
from app.services.audit_service import append_audit_log
from app.services.operations_health_service import read_worker_heartbeat
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


# An unpaid order is shown as abandoned after this long. The stored status stays
# "pending", so a late payment is still accepted by the webhook.
ORDER_EXPIRES_AFTER = timedelta(hours=24)
ORDER_DISPLAY_STATUSES = (
    "pending",
    "paid",
    "partially_refunded",
    "refunded",
    "failed",
    "expired",
)


def _order_refunded_kopecks():
    """Processed refunds of the order's purchase; requires Purchase outer-joined."""
    return func.coalesce(
        select(func.sum(RefundRequest.amount_kopecks))
        .where(
            RefundRequest.purchase_id == Purchase.id,
            RefundRequest.status == "processed",
        )
        .correlate(Purchase)
        .scalar_subquery(),
        0,
    )


def _order_refundable_kopecks():
    """What a new refund request may still claim (mirrors RefundService.create_refund)."""
    allocated = func.coalesce(
        select(func.sum(RefundRequest.amount_kopecks))
        .where(
            RefundRequest.purchase_id == Purchase.id,
            RefundRequest.status != "rejected",
        )
        .correlate(Purchase)
        .scalar_subquery(),
        0,
    )
    return case(
        (Purchase.id.is_(None), 0),
        else_=func.greatest(Purchase.amount_kopecks - allocated, 0),
    )


def _order_failed_attempt_exists():
    """The provider reported an unsuccessful attempt for this order."""
    reference = literal("order|") + cast(Order.id, String)
    return (
        select(PaymentEvent.id)
        .where(
            PaymentEvent.processing_status == "ignored",
            or_(
                PaymentEvent.order_id == Order.id,
                PaymentEvent.order_reference == reference,
                # Callbacks from the old field mapping carried the reference here.
                PaymentEvent.external_event_id == reference,
            ),
        )
        .correlate(Order)
        .exists()
    )


PAYMENT_INCIDENT_WINDOW = timedelta(days=30)


def _payment_identities(event):
    """(provider payment id, merchant order reference) of a journaled event.

    Mirrors payments._resolve_payment_key: callbacks from the old field mapping
    carried the merchant reference ("order|..." / "course|...") in ``order_id``
    (external_event_id) and the provider payment id in ``order_num``
    (order_reference). Normalise both before deduplicating.
    """
    legacy_order = or_(
        event.external_event_id.like("order|%"),
        event.external_event_id.like("course|%"),
    )
    payment_id = case(
        (and_(event.external_event_id.is_not(None), ~legacy_order), event.external_event_id),
        (legacy_order, event.order_reference),
        else_=None,
    )
    order_reference = case(
        (legacy_order, event.external_event_id),
        else_=event.order_reference,
    )
    return payment_id, order_reference


def _payment_incident_count_query(since: datetime | None = None):
    """Distinct unresolved payment incidents, not raw journal rows.

    Every provider delivery (with its own ``attempt``) is a separate row, so one
    rejected payment yields several. An incident is one provider payment id (or,
    without it, one order reference), both normalised as the webhook does; a
    rejection is resolved once a later delivery for the same order or payment
    was processed.
    """
    later = aliased(PaymentEvent)
    payment_id, order_reference = _payment_identities(PaymentEvent)
    later_payment_id, later_order_reference = _payment_identities(later)
    resolved = (
        select(later.id)
        .where(
            later.processing_status == "processed",
            later.received_at > PaymentEvent.received_at,
            or_(
                and_(PaymentEvent.order_id.is_not(None), later.order_id == PaymentEvent.order_id),
                and_(order_reference.is_not(None), later_order_reference == order_reference),
                and_(payment_id.is_not(None), later_payment_id == payment_id),
            ),
        )
        .correlate(PaymentEvent)
        .exists()
    )
    incident_key = func.coalesce(payment_id, order_reference, cast(PaymentEvent.id, String))
    conditions = [
        PaymentEvent.processing_status.in_(["rejected", "financial_incident"]),
        or_(PaymentEvent.processing_status != "rejected", ~resolved),
    ]
    if since is not None:
        conditions.append(PaymentEvent.received_at >= since)
    return select(func.count(func.distinct(incident_key))).where(*conditions)

def order_display_status(now: datetime):
    """Derived order status; requires Purchase outer-joined on Purchase.order_id."""
    refunded = _order_refunded_kopecks()
    is_paid = or_(Order.status == "paid", Purchase.payment_status == "success")
    return case(
        (
            is_paid,
            case(
                (
                    and_(refunded > 0, refunded >= Purchase.amount_kopecks),
                    literal("refunded"),
                ),
                (refunded > 0, literal("partially_refunded")),
                else_=literal("paid"),
            ),
        ),
        (_order_failed_attempt_exists(), literal("failed")),
        (Order.created_at < now - ORDER_EXPIRES_AFTER, literal("expired")),
        else_=literal("pending"),
    )


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
    outbox_retry: int
    outbox_processing: int
    outbox_dead_letter: int
    # Age of the oldest message still waiting for delivery (pending, retry, processing).
    oldest_undelivered_seconds: int | None
    # "alive", "missing" or "unknown" (Redis not configured or unavailable).
    worker_heartbeat: str
    # None while the heartbeat is unknown: never reported as healthy.
    worker_alive: bool | None
    worker_heartbeat_age_seconds: int | None
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


class AccessCourseItem(BaseModel):
    id: UUID
    title: str
    access_days: int


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


class LoginLinkRequest(BaseModel):
    reason: str = Field(default="Отправлена ссылка для входа", min_length=5, max_length=1000)


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
    # Derived display status: pending, paid, partially_refunded, refunded, failed, expired.
    status: str
    # Raw orders.status as written by checkout and the webhook (pending or paid).
    order_status: str
    purchase_id: UUID | None
    refunded_kopecks: int
    refundable_kopecks: int
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
    # False when the student has another active access to the course that ends
    # later: only the latest access may be extended.
    is_latest_access: bool = True


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


RETRYABLE_NOTIFICATION_STATUSES = frozenset({"retry", "dead_letter"})


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
    total_students = await db.scalar(select(func.count(User.id)).where(student_account_filter()))
    active_entitlements = await db.scalar(
        select(func.count(Entitlement.id)).where(
            Entitlement.status == "active", Entitlement.expires_at > now
        )
    )
    gross = await db.scalar(
        select(func.coalesce(func.sum(Purchase.amount_kopecks), 0)).where(
            paid_financial_filter()
        )
    )
    refunded = await db.scalar(
        select(func.coalesce(func.sum(RefundRequest.amount_kopecks), 0))
        .join(Purchase, Purchase.id == RefundRequest.purchase_id)
        .where(
            RefundRequest.status == "processed", paid_financial_filter()
        )
    )
    pending_orders = await db.scalar(
        select(func.count(Order.id))
        .select_from(Order)
        .outerjoin(Purchase, Purchase.order_id == Order.id)
        .where(order_display_status(now) == "pending")
    )
    payment_errors = await db.scalar(
        _payment_incident_count_query(since=now - PAYMENT_INCIDENT_WINDOW)
    )
    dead_letters = await db.scalar(
        select(func.count(OutboxMessage.id)).where(OutboxMessage.status == "dead_letter")
    )
    # After an early renewal a student holds two active rows; only the latest
    # effective access end per student and course says whether access is ending.
    latest_access = (
        select(func.max(Entitlement.expires_at).label("access_end"))
        .where(Entitlement.status == "active", Entitlement.expires_at > now)
        .group_by(Entitlement.user_id, Entitlement.course_id)
        .subquery()
    )
    expiring = await db.scalar(
        select(func.count()).select_from(latest_access).where(latest_access.c.access_end <= week)
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
    counts = dict(
        (
            await db.execute(
                select(OutboxMessage.status, func.count(OutboxMessage.id)).group_by(
                    OutboxMessage.status
                )
            )
        ).all()
    )
    oldest_undelivered = await db.scalar(
        select(func.min(OutboxMessage.created_at)).where(
            OutboxMessage.status.in_(["pending", "retry", "processing"])
        )
    )
    heartbeat = await read_worker_heartbeat()
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
        outbox_pending=int(counts.get("pending", 0)),
        outbox_retry=int(counts.get("retry", 0)),
        outbox_processing=int(counts.get("processing", 0)),
        outbox_dead_letter=int(counts.get("dead_letter", 0)),
        oldest_undelivered_seconds=(
            max(0, int((datetime.utcnow() - oldest_undelivered).total_seconds()))
            if oldest_undelivered
            else None
        ),
        worker_heartbeat=heartbeat.state,
        worker_alive=None if heartbeat.state == "unknown" else heartbeat.state == "alive",
        worker_heartbeat_age_seconds=heartbeat.age_seconds,
        last_payment_event_at=last_payment,
    )


@router.get("/access-courses", response_model=list[AccessCourseItem])
async def access_courses(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("access.manage")),
):
    rows = await db.execute(select(Course.id, Course.title, Course.access_days).order_by(Course.title, Course.id))
    return [AccessCourseItem(id=row.id, title=row.title, access_days=row.access_days) for row in rows]


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
        .order_by(User.created_at.desc(), User.id.desc())
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
    notification_kind = AccessService.enqueue_manual_grant_notification(
        db, user=user, course=course, entitlement=entitlement, new_account=user_created
    )
    if user_created:
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
    data: LoginLinkRequest | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("users.manage")),
):
    """Email the student a one-time link to set a password and sign in."""
    data = data or LoginLinkRequest()
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # The link sets a new password, so it must never reach a team account
    # (legacy admin role or any RBAC role assignment).
    team_assignment = await db.scalar(
        select(UserRoleAssignment.id).where(UserRoleAssignment.user_id == user.id).limit(1)
    )
    if user.role != "student" or team_assignment is not None:
        raise HTTPException(
            status_code=409,
            detail="Ссылку для входа можно отправить только ученику",
        )
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
        reason=data.reason,
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
    now = datetime.utcnow()
    # An active row whose end has passed is expired, even before the lifecycle
    # scan rewrites it (same rule as /admin/purchases).
    effective_status = case(
        (
            and_(Entitlement.status == "active", Entitlement.expires_at <= now),
            literal("expired"),
        ),
        else_=Entitlement.status,
    )
    later = aliased(Entitlement)
    is_latest = ~(
        select(later.id)
        .where(
            later.user_id == Entitlement.user_id,
            later.course_id == Entitlement.course_id,
            later.id != Entitlement.id,
            later.status == "active",
            later.expires_at > Entitlement.expires_at,
        )
        .correlate(Entitlement)
        .exists()
    )
    conditions = []
    if search:
        conditions.append(User.email.ilike(f"%{search.strip()}%"))
    if status_filter:
        conditions.append(effective_status == status_filter)
    if expiring_days:
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
            select(Entitlement, User.email, Course.title, effective_status.label("effective_status"), is_latest.label("is_latest"))
            .join(User, User.id == Entitlement.user_id)
            .join(Course, Course.id == Entitlement.course_id)
            .where(*conditions)
            .order_by(Entitlement.expires_at.desc(), Entitlement.id.desc())
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
                status=row_status,
                starts_at=item.starts_at,
                expires_at=item.expires_at,
                reason=item.reason,
                revoked_at=item.revoked_at,
                is_latest_access=bool(latest),
            )
            for item, email, course_title, row_status, latest in rows
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
    if search and can_read_pii:
        conditions.append(Order.customer_email.ilike(f"%{search.strip()}%"))
    elif search:
        # Masked readers may only look up an address they already know; partial
        # matches would let them recover hidden emails character by character.
        conditions.append(func.lower(Order.customer_email) == search.strip().lower())
    display_status = order_display_status(datetime.utcnow())
    if status_filter:
        conditions.append(display_status == status_filter)
    total = await db.scalar(
        select(func.count(Order.id))
        .select_from(Order)
        .outerjoin(Purchase, Purchase.order_id == Order.id)
        .where(*conditions)
    )
    rows = (
        await db.execute(
            select(
                Order,
                Purchase.id,
                display_status.label("display_status"),
                _order_refunded_kopecks().label("refunded_kopecks"),
                _order_refundable_kopecks().label("refundable_kopecks"),
            )
            .outerjoin(Purchase, Purchase.order_id == Order.id)
            .where(*conditions)
            .order_by(Order.created_at.desc(), Order.id.desc())
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
                status=row_status,
                order_status=order.status,
                purchase_id=purchase_id,
                refunded_kopecks=int(refunded or 0),
                refundable_kopecks=int(refundable or 0),
                paid_at=order.paid_at,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )
            for order, purchase_id, row_status, refunded, refundable in rows
        ],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get("/notifications", response_model=NotificationPage)
async def list_notifications(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    channel: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("notifications.manage")),
):
    conditions = []
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(or_(OutboxMessage.recipient.ilike(pattern), OutboxMessage.kind.ilike(pattern)))
    if status_filter:
        conditions.append(OutboxMessage.status == status_filter)
    if channel:
        conditions.append(OutboxMessage.channel == channel)
    total = await db.scalar(select(func.count(OutboxMessage.id)).where(*conditions))
    items = (
        await db.execute(
            select(OutboxMessage)
            .where(*conditions)
            .order_by(OutboxMessage.created_at.desc(), OutboxMessage.id.desc())
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
    # Lock the row so a worker cannot claim or finish it between the check and the reset.
    message = await db.scalar(
        select(OutboxMessage).where(OutboxMessage.id == message_id).with_for_update()
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if message.status not in RETRYABLE_NOTIFICATION_STATUSES:
        # get_db rolls back on the exception, which releases the row lock.
        raise HTTPException(
            status_code=409,
            detail=(
                f"Повтор невозможен: уведомление в статусе «{message.status}». "
                "Повторить можно только сообщения в статусах retry и dead_letter."
            ),
        )
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
    # Same definitions as the orders list: failed and expired orders are settled,
    # only a genuinely open order without an answer is stale.
    stale = await db.scalar(
        select(func.count(Order.id))
        .select_from(Order)
        .outerjoin(Purchase, Purchase.order_id == Order.id)
        .where(
            order_display_status(now) == "pending",
            Order.created_at < now - timedelta(hours=2),
        )
    )
    # Same incident definition as the dashboard, without its 30-day window:
    # an unresolved incident stays on the reconciliation list until handled.
    payment_errors = await db.scalar(_payment_incident_count_query())
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
            paid_financial_filter(),
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
