"""Date-filtered management reports backed by server-side source-of-truth data."""

import csv
import io
from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.analytics_event import AnalyticsEvent
from app.models.certificate import Certificate
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.progress import Progress
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.models.user import User


router = APIRouter()


class ReportOverview(BaseModel):
    date_from: date
    date_to: date
    gross_revenue_kopecks: int
    refunded_kopecks: int
    net_revenue_kopecks: int
    paid_orders: int
    pending_orders: int
    new_students: int


class FunnelStage(BaseModel):
    event_name: str
    label: str
    count: int
    conversion_from_previous_pct: float | None


class FunnelReport(BaseModel):
    stages: list[FunnelStage]


class DeliveryReport(BaseModel):
    total: int
    sent: int
    pending: int
    retry: int
    dead_letter: int
    success_rate_pct: float


FUNNEL = [
    ("landing_view", "Просмотр лендинга"),
    ("cta_click", "Клик по CTA"),
    ("checkout_started", "Начало checkout"),
    ("payment_redirect", "Переход к оплате"),
    ("purchase_confirmed", "Подтверждённая оплата"),
]


def _date_bounds(date_from: date | None, date_to: date | None) -> tuple[date, date, datetime, datetime]:
    end_date = date_to or datetime.utcnow().date()
    start_date = date_from or end_date - timedelta(days=29)
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="date_from must not exceed date_to")
    if (end_date - start_date).days > 730:
        raise HTTPException(status_code=422, detail="Report range cannot exceed 730 days")
    return (
        start_date,
        end_date,
        datetime.combine(start_date, time.min),
        datetime.combine(end_date + timedelta(days=1), time.min),
    )


def _money_date_filter(start: datetime, end: datetime):
    return and_(
        func.coalesce(Purchase.paid_at, Purchase.created_at) >= start,
        func.coalesce(Purchase.paid_at, Purchase.created_at) < end,
    )


@router.get("/reports/overview", response_model=ReportOverview)
async def report_overview(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    start_date, end_date, start, end = _date_bounds(date_from, date_to)
    purchase_filter = and_(Purchase.payment_status == "success", _money_date_filter(start, end))
    gross = await db.scalar(select(func.coalesce(func.sum(Purchase.amount_kopecks), 0)).where(purchase_filter))
    paid_orders = await db.scalar(select(func.count(Purchase.id)).where(purchase_filter))
    refunded = await db.scalar(
        select(func.coalesce(func.sum(RefundRequest.amount_kopecks), 0)).where(
            RefundRequest.status == "processed",
            RefundRequest.processed_at >= start,
            RefundRequest.processed_at < end,
        )
    )
    pending = await db.scalar(
        select(func.count(Order.id)).where(
            Order.status == "pending", Order.created_at >= start, Order.created_at < end
        )
    )
    new_students = await db.scalar(
        select(func.count(User.id)).where(
            User.role == "student", User.created_at >= start, User.created_at < end
        )
    )
    gross_value = int(gross or 0)
    refunded_value = int(refunded or 0)
    return ReportOverview(
        date_from=start_date,
        date_to=end_date,
        gross_revenue_kopecks=gross_value,
        refunded_kopecks=refunded_value,
        net_revenue_kopecks=gross_value - refunded_value,
        paid_orders=int(paid_orders or 0),
        pending_orders=int(pending or 0),
        new_students=int(new_students or 0),
    )


@router.get("/reports/timeseries")
async def report_timeseries(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    start_date, end_date, start, end = _date_bounds(date_from, date_to)
    payment_day = func.date(func.coalesce(Purchase.paid_at, Purchase.created_at))
    payment_rows = (
        await db.execute(
            select(
                payment_day,
                func.count(Purchase.id),
                func.coalesce(func.sum(Purchase.amount_kopecks), 0),
            )
            .where(Purchase.payment_status == "success", _money_date_filter(start, end))
            .group_by(payment_day)
        )
    ).all()
    refund_day = func.date(RefundRequest.processed_at)
    refund_rows = (
        await db.execute(
            select(refund_day, func.coalesce(func.sum(RefundRequest.amount_kopecks), 0))
            .where(
                RefundRequest.status == "processed",
                RefundRequest.processed_at >= start,
                RefundRequest.processed_at < end,
            )
            .group_by(refund_day)
        )
    ).all()
    payments = {row[0]: (int(row[1]), int(row[2])) for row in payment_rows}
    refunds = {row[0]: int(row[1]) for row in refund_rows}
    points = []
    current = start_date
    while current <= end_date:
        orders, gross = payments.get(current, (0, 0))
        refunded = refunds.get(current, 0)
        points.append(
            {
                "date": current,
                "orders": orders,
                "gross_revenue_kopecks": gross,
                "refunded_kopecks": refunded,
                "net_revenue_kopecks": gross - refunded,
            }
        )
        current += timedelta(days=1)
    return points


@router.get("/reports/funnel", response_model=FunnelReport)
async def report_funnel(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    _, _, start, end = _date_bounds(date_from, date_to)
    rows = (
        await db.execute(
            select(
                AnalyticsEvent.event_name,
                AnalyticsEvent.happened_at,
                AnalyticsEvent.anonymous_id,
                AnalyticsEvent.user_id,
                AnalyticsEvent.order_id,
            ).where(
                AnalyticsEvent.event_name.in_([item[0] for item in FUNNEL]),
                AnalyticsEvent.happened_at >= start,
                AnalyticsEvent.happened_at < end,
            )
        )
    ).all()

    # Join anonymous, user, and order identifiers through bridge events such as
    # checkout_started. Then count distinct entities that reached every stage
    # in order; repeated clicks and orphan purchases cannot inflate conversion.
    parents: dict[str, str] = {}

    def find(item: str) -> str:
        parents.setdefault(item, item)
        while parents[item] != item:
            parents[item] = parents[parents[item]]
            item = parents[item]
        return item

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    identified_rows: list[tuple[str, datetime, str]] = []
    for event_name, happened_at, anonymous_id, user_id, order_id in rows:
        identifiers = [
            value
            for value in (
                f"anonymous:{anonymous_id}" if anonymous_id else None,
                f"user:{user_id}" if user_id else None,
                f"order:{order_id}" if order_id else None,
            )
            if value is not None
        ]
        if not identifiers:
            continue
        for identifier in identifiers[1:]:
            union(identifiers[0], identifier)
        identified_rows.append((event_name, happened_at, identifiers[0]))

    entity_stages: dict[str, dict[str, datetime]] = {}
    for event_name, happened_at, identifier in identified_rows:
        stages_for_entity = entity_stages.setdefault(find(identifier), {})
        previous_time = stages_for_entity.get(event_name)
        if previous_time is None or happened_at < previous_time:
            stages_for_entity[event_name] = happened_at

    counts = {event_name: 0 for event_name, _ in FUNNEL}
    for reached in entity_stages.values():
        previous_time: datetime | None = None
        for event_name, _ in FUNNEL:
            happened_at = reached.get(event_name)
            if happened_at is None or (
                previous_time is not None and happened_at < previous_time
            ):
                break
            counts[event_name] += 1
            previous_time = happened_at
    stages = []
    previous = None
    for event_name, label in FUNNEL:
        count = counts.get(event_name, 0)
        conversion = None if previous in (None, 0) else round(count / previous * 100, 2)
        stages.append(
            FunnelStage(
                event_name=event_name,
                label=label,
                count=count,
                conversion_from_previous_pct=conversion,
            )
        )
        previous = count
    return FunnelReport(stages=stages)


async def _source_rows(db: AsyncSession, start: datetime, end: datetime):
    source = func.coalesce(Order.first_utm_source, "(direct)").label("source")
    rows = (
        await db.execute(
            select(
                source,
                func.count(Order.id).label("orders"),
                func.count(Purchase.id).label("paid_orders"),
                func.coalesce(func.sum(Purchase.amount_kopecks), 0).label("gross"),
            )
            .outerjoin(
                Purchase,
                and_(Purchase.order_id == Order.id, Purchase.payment_status == "success"),
            )
            .where(Order.created_at >= start, Order.created_at < end)
            .group_by(source)
            .order_by(func.coalesce(func.sum(Purchase.amount_kopecks), 0).desc())
        )
    ).all()
    return [
        {
            "source": row.source,
            "orders": int(row.orders),
            "paid_orders": int(row.paid_orders),
            "gross_revenue_kopecks": int(row.gross),
            "conversion_pct": round(row.paid_orders / row.orders * 100, 2) if row.orders else 0,
        }
        for row in rows
    ]


@router.get("/reports/sources")
async def report_sources(
    date_from: date | None = None,
    date_to: date | None = None,
    format: Literal["json", "csv"] = Query(default="json"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    _, _, start, end = _date_bounds(date_from, date_to)
    rows = await _source_rows(db, start, end)
    if format == "json":
        return rows
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else ["source"])
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=analytics-sources.csv"},
    )


@router.get("/reports/tariffs")
async def report_tariffs(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    _, _, start, end = _date_bounds(date_from, date_to)
    rows = (
        await db.execute(
            select(
                Purchase.tariff,
                func.count(Purchase.id),
                func.coalesce(func.sum(Purchase.amount_kopecks), 0),
            )
            .where(Purchase.payment_status == "success", _money_date_filter(start, end))
            .group_by(Purchase.tariff)
        )
    ).all()
    return [
        {"tariff": tariff, "paid_orders": int(count), "gross_revenue_kopecks": int(gross)}
        for tariff, count, gross in rows
    ]


@router.get("/reports/cohorts")
async def report_cohorts(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    _, _, start, end = _date_bounds(date_from, date_to)
    cohort = func.date_trunc("month", User.created_at).label("cohort")
    rows = (
        await db.execute(
            select(
                cohort,
                func.count(func.distinct(User.id)),
                func.count(func.distinct(Purchase.user_id)),
                func.count(func.distinct(Certificate.user_id)),
            )
            .outerjoin(
                Purchase,
                and_(Purchase.user_id == User.id, Purchase.payment_status == "success"),
            )
            .outerjoin(Certificate, Certificate.user_id == User.id)
            .where(User.role == "student", User.created_at >= start, User.created_at < end)
            .group_by(cohort)
            .order_by(cohort)
        )
    ).all()
    return [
        {
            "cohort": item.date().isoformat(),
            "students": int(students),
            "purchasers": int(purchasers),
            "certified_students": int(certified),
        }
        for item, students, purchasers, certified in rows
    ]


@router.get("/reports/progress")
async def report_progress(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    _, _, start, end = _date_bounds(date_from, date_to)
    active_students = await db.scalar(
        select(func.count(func.distinct(Progress.user_id))).where(
            Progress.updated_at >= start, Progress.updated_at < end
        )
    )
    completed_lessons = await db.scalar(
        select(func.count(Progress.id)).where(
            Progress.is_completed.is_(True),
            Progress.completed_at >= start,
            Progress.completed_at < end,
        )
    )
    certificates = await db.scalar(
        select(func.count(Certificate.id)).where(
            Certificate.status == "active",
            Certificate.issued_at >= start,
            Certificate.issued_at < end,
        )
    )
    return {
        "active_students": int(active_students or 0),
        "completed_lessons": int(completed_lessons or 0),
        "certificates_issued": int(certificates or 0),
    }


@router.get("/reports/refunds")
async def report_refunds(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    _, _, start, end = _date_bounds(date_from, date_to)
    rows = (
        await db.execute(
            select(
                RefundRequest.status,
                func.count(RefundRequest.id),
                func.coalesce(func.sum(RefundRequest.amount_kopecks), 0),
            )
            .where(RefundRequest.created_at >= start, RefundRequest.created_at < end)
            .group_by(RefundRequest.status)
        )
    ).all()
    return [
        {"status": status, "requests": int(count), "amount_kopecks": int(amount)}
        for status, count, amount in rows
    ]


@router.get("/reports/delivery", response_model=DeliveryReport)
async def report_delivery(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("analytics.read")),
):
    _, _, start, end = _date_bounds(date_from, date_to)
    rows = (
        await db.execute(
            select(OutboxMessage.status, func.count(OutboxMessage.id))
            .where(OutboxMessage.created_at >= start, OutboxMessage.created_at < end)
            .group_by(OutboxMessage.status)
        )
    ).all()
    counts = {status: int(count) for status, count in rows}
    total = sum(counts.values())
    sent = counts.get("sent", 0)
    return DeliveryReport(
        total=total,
        sent=sent,
        pending=counts.get("pending", 0),
        retry=counts.get("retry", 0),
        dead_letter=counts.get("dead_letter", 0) + counts.get("dead", 0),
        success_rate_pct=round(sent / total * 100, 2) if total else 0,
    )
