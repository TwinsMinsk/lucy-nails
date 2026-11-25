"""Owner alerts about orders and accounts, queued through the outbox.

Every alert names the customer's email and the order reference so that an
operator can match a customer who writes to support. The alerts go to the
owner's chat or to the help desk «Оплаты» topic (see owner_alert_target).

These alerts are optional: queueing one must never undo the customer action
it reports. Each is queued inside a savepoint, a failure rolls back only the
savepoint, and a missed «Новый заказ» is queued later by the lifecycle scan
from the stored order (stable dedupe key).
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import String, and_, cast, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.models.order import Order
from app.models.outbox import OutboxMessage
from app.models.purchase import Purchase, paid_financial_filter
from app.models.user import User
from app.services.outbox_service import (
    enqueue_owner_telegram_alert,
    format_rub,
    owner_alert_target,
)
from app.services.support_links import order_reference

logger = logging.getLogger(__name__)

# Orders older than this are never reported as abandoned, so the first scan
# after deployment does not flood the chat with historical checkouts.
ABANDONED_ORDER_MAX_AGE = timedelta(days=1)
ABANDONED_ORDER_BATCH = 50
# A «Новый заказ» that could not be queued with its order is recovered for
# orders this recent, a bounded batch per lifecycle pass.
ORDER_ALERT_RECOVERY_WINDOW = timedelta(days=1)
ORDER_ALERT_RECOVERY_BATCH = 50


def _abandoned_dedupe_key(order_id: UUID) -> str:
    return f"order:{order_id}:abandoned"


def _created_dedupe_key(order_id: UUID) -> str:
    return f"order:{order_id}:created"


async def _queue_optional_alert(db: AsyncSession, queue) -> bool:
    """Run ``queue()`` in a savepoint; a failure never reaches the caller.

    The caller's own pending changes are flushed first, outside the
    savepoint, so their errors still surface where they belong. Inside, the
    explicit flush makes a failing insert fail here and not at the caller's
    next autoflush or commit.
    """
    await db.flush()
    try:
        async with db.begin_nested():
            queued = await queue()
            await db.flush()
    except Exception as exc:
        # The exception text can carry SQL parameters, emails among them.
        logger.warning(
            "Owner alert not queued (%s); the customer action is kept", type(exc).__name__
        )
        return False
    return bool(queued)


def _attribution_lines(order: Order) -> str:
    # First touch is the attribution model of the reports; the last touch is
    # the fallback for a visit that only carries it.
    source = order.first_utm_source or order.last_utm_source
    campaign = order.first_utm_campaign or order.last_utm_campaign
    lines = ""
    if source:
        lines += f"Источник: {source}\n"
    if campaign:
        lines += f"Кампания: {campaign}\n"
    return lines


async def enqueue_order_created_alert(db: AsyncSession, order: Order) -> bool:
    """«🧾 Новый заказ», once per order, without risking the order itself."""
    text = (
        "🧾 Новый заказ\n"
        f"Сумма: {format_rub(order.amount_kopecks)}\n"
        f"Курс: {order.course_title}\n"
        f"Email: {order.customer_email}\n"
        + _attribution_lines(order)
        + f"Заказ: {order_reference(order.id)}"
    )
    dedupe_key = _created_dedupe_key(order.id)
    return await _queue_optional_alert(
        db,
        lambda: enqueue_owner_telegram_alert(
            db, kind="owner_order_created", text=text, dedupe_key=dedupe_key
        ),
    )


async def schedule_missing_order_created_alerts(
    db: AsyncSession,
    *,
    now: datetime,
    limit: int = ORDER_ALERT_RECOVERY_BATCH,
) -> int:
    """Queue «🧾 Новый заказ» for recent orders whose alert is missing.

    The checkout queues it with the order; when that failed, the order is
    still committed and this pass finds it by the alert's dedupe key.
    """
    if owner_alert_target() is None:
        return 0
    dedupe_key = func.concat("order:", cast(Order.id, String), ":created")
    rows = await db.execute(
        select(Order)
        .where(
            Order.created_at > now - ORDER_ALERT_RECOVERY_WINDOW,
            ~exists().where(OutboxMessage.dedupe_key == dedupe_key),
        )
        .order_by(Order.created_at)
        .limit(limit)
    )
    scheduled = 0
    for order in rows.scalars().all():
        scheduled += int(await enqueue_order_created_alert(db, order))
    return scheduled


async def schedule_abandoned_order_alerts(
    db: AsyncSession,
    *,
    now: datetime,
    limit: int = ABANDONED_ORDER_BATCH,
) -> int:
    """Queue «⏳ Заказ не оплачен» for pending orders past the configured delay.

    Only orders whose age is inside a window just past the delay are looked
    at: from N minutes to N plus the window width, which is N but at least two
    scan intervals, so consecutive scans leave no gap. The first scan after
    the feature is deployed therefore never reports the backlog of older
    unpaid orders. The selection happens in the database and is bounded:
    already reported orders and orders whose buyer has since paid for the
    same course are excluded there, so they never fill the batch.
    """
    minutes = settings.ORDER_ABANDONED_ALERT_MINUTES
    if minutes <= 0 or owner_alert_target() is None:
        return 0
    delay = timedelta(minutes=minutes)
    width = max(delay, timedelta(seconds=2 * settings.LIFECYCLE_SCAN_SECONDS))
    cutoff = now - delay
    oldest = max(now - delay - width, now - ABANDONED_ORDER_MAX_AGE)
    dedupe_key = func.concat("order:", cast(Order.id, String), ":abandoned")
    later_order = aliased(Order)
    rows = await db.execute(
        select(Order)
        .where(
            Order.status == "pending",
            Order.created_at <= cutoff,
            Order.created_at > oldest,
            ~exists().where(OutboxMessage.dedupe_key == dedupe_key),
            ~exists().where(
                and_(
                    func.lower(later_order.customer_email) == func.lower(Order.customer_email),
                    later_order.course_id == Order.course_id,
                    later_order.status == "paid",
                    later_order.created_at >= Order.created_at,
                )
            ),
        )
        .order_by(Order.created_at)
        .limit(limit)
    )
    scheduled = 0
    for order in rows.scalars().all():
        scheduled += int(
            await enqueue_owner_telegram_alert(
                db,
                kind="owner_order_abandoned",
                text=(
                    "⏳ Заказ не оплачен\n"
                    f"Сумма: {format_rub(order.amount_kopecks)}\n"
                    f"Курс: {order.course_title}\n"
                    f"Email: {order.customer_email}\n"
                    f"Заказ: {order_reference(order.id)}"
                ),
                dedupe_key=_abandoned_dedupe_key(order.id),
            )
        )
    return scheduled


async def enqueue_account_activated_alert(db: AsyncSession, user: User) -> bool:
    """«🔑 Аккаунт активирован» for an account that has a paid purchase.

    The activation link also confirms self-registered and admin-created
    accounts; only buyers are reported. The lookup and the insert run in a
    savepoint, so a failure never undoes the new password.
    """
    user_id, email = user.id, user.email

    async def queue() -> bool:
        # Real payments only: historical manual grants are stored as purchases too.
        purchase = await db.scalar(
            select(Purchase)
            .where(Purchase.user_id == user_id, paid_financial_filter())
            .order_by(Purchase.paid_at.desc().nulls_last(), Purchase.created_at.desc())
            .limit(1)
        )
        if purchase is None:
            return False
        reference = order_reference(purchase.order_id) if purchase.order_id else "—"
        return await enqueue_owner_telegram_alert(
            db,
            kind="owner_account_activated",
            text=(
                "🔑 Аккаунт активирован\n"
                f"Email: {email}\n"
                f"Заказ: {reference}"
            ),
            dedupe_key=f"user:{user_id}:activated",
        )

    return await _queue_optional_alert(db, queue)


async def payment_alert_email_lines(
    db: AsyncSession,
    order_id: UUID | None,
    form_email: str,
) -> str:
    """Email lines for a rejected-payment alert.

    Support is asked about the account of the checkout email, so a matched
    order shows that one, plus the payment-form email when it differs. The
    lookup only enriches the text: when it fails, the payment-form email is
    used and the webhook keeps its planned answer.
    """
    form_email = form_email.strip()
    checkout_email = None
    if order_id is not None:
        try:
            checkout_email = await db.scalar(
                select(Order.customer_email).where(Order.id == order_id)
            )
        except Exception as exc:
            logger.warning(
                "Checkout email lookup for a payment alert failed (%s); "
                "using the payment-form email",
                type(exc).__name__,
            )
            checkout_email = None
    if not checkout_email:
        return f"Email: {form_email or '—'}\n"
    lines = f"Email: {checkout_email}\n"
    if form_email and form_email.lower() != checkout_email.strip().lower():
        lines += f"Email в форме оплаты: {form_email}\n"
    return lines
