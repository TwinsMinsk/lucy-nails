"""Idempotent access lifecycle notifications and operational Telegram alerts."""

import math
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.outbox import OutboxMessage
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.services.access_service import AccessService
from app.services.outbox_service import enqueue_outbox_message


class LifecycleService:
    REMINDER_DAYS = {7, 3, 1}

    @staticmethod
    async def _enqueue_once(
        db: AsyncSession,
        *,
        kind: str,
        channel: str,
        recipient: str,
        payload: dict,
        dedupe_key: str,
    ) -> bool:
        existing = await db.scalar(
            select(OutboxMessage.id).where(OutboxMessage.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return False
        enqueue_outbox_message(
            db,
            kind=kind,
            channel=channel,
            recipient=recipient,
            payload=payload,
            dedupe_key=dedupe_key,
        )
        return True

    @classmethod
    async def schedule(cls, db: AsyncSession, *, now: datetime | None = None) -> int:
        now = now or datetime.utcnow()
        rows = (
            await db.execute(
                select(Entitlement, User, Course)
                .join(User, User.id == Entitlement.user_id)
                .join(Course, Course.id == Entitlement.course_id)
                .where(Entitlement.status == "active")
            )
        ).all()
        scheduled = 0

        for entitlement, user, course in rows:
            if entitlement.expires_at <= now:
                entitlement.status = "expired"
                scheduled += await cls._enqueue_once(
                    db,
                    kind="access_expired",
                    channel="email",
                    recipient=user.email,
                    payload={"course_title": course.title},
                    dedupe_key=f"entitlement:{entitlement.id}:expired:email",
                )
                if settings.TELEGRAM_BOT_TOKEN and user.telegram_id is not None:
                    scheduled += await cls._enqueue_once(
                        db,
                        kind="access_expired",
                        channel="telegram",
                        recipient=str(user.telegram_id),
                        payload={
                            "text": f"Срок доступа к курсу «{course.title}» завершён."
                        },
                        dedupe_key=f"entitlement:{entitlement.id}:expired:telegram",
                    )
                    scheduled += int(
                        await AccessService.enqueue_support_group_removal(
                            db,
                            entitlement,
                            dedupe_suffix="group-remove:expired",
                        )
                    )
                await AnalyticsService.record_event(
                    db,
                    event_id=f"access_expired:{entitlement.id}",
                    event_name="access_expired",
                    source="server",
                    user_id=user.id,
                    course_id=course.id,
                    properties={"tariff": entitlement.tariff},
                )
                continue

            days_left = math.ceil(
                (entitlement.expires_at - now).total_seconds() / 86400
            )
            if days_left not in cls.REMINDER_DAYS:
                continue
            payload = {
                "course_title": course.title,
                "days": days_left,
                "expires_at": entitlement.expires_at.isoformat(),
            }
            scheduled += await cls._enqueue_once(
                db,
                kind="access_expiry_reminder",
                channel="email",
                recipient=user.email,
                payload=payload,
                dedupe_key=f"entitlement:{entitlement.id}:reminder:{days_left}:email",
            )
            if settings.TELEGRAM_BOT_TOKEN and user.telegram_id is not None:
                scheduled += await cls._enqueue_once(
                    db,
                    kind="access_expiry_reminder",
                    channel="telegram",
                    recipient=str(user.telegram_id),
                    payload={
                        "text": (
                            f"Доступ к курсу «{course.title}» закончится через "
                            f"{days_left} дн. Продолжите обучение в личном кабинете."
                        )
                    },
                    dedupe_key=(
                        f"entitlement:{entitlement.id}:reminder:{days_left}:telegram"
                    ),
                )

        scheduled += await cls._schedule_owner_alert(db, now=now)
        return scheduled

    @classmethod
    async def _schedule_owner_alert(cls, db: AsyncSession, *, now: datetime) -> int:
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_OWNER_CHAT_ID is None:
            return 0
        # Rejected payments are alerted one by one when the webhook arrives, so this
        # digest only covers undelivered notifications. Alert when their number
        # changes, and repeat at most once a day while they stay unresolved.
        dead_letters = await db.scalar(
            select(func.count(OutboxMessage.id)).where(
                OutboxMessage.status == "dead_letter"
            )
        )
        if not dead_letters:
            return 0
        day_key = now.strftime("%Y%m%d")
        return int(
            await cls._enqueue_once(
                db,
                kind="system_alert",
                channel="telegram",
                recipient=str(settings.TELEGRAM_OWNER_CHAT_ID),
                payload={
                    "text": (
                        "⚠️ Lucy Nails: не доставлено уведомлений: "
                        f"{dead_letters}. Откройте админку → «Уведомления» "
                        "и отправьте их повторно."
                    )
                },
                dedupe_key=f"system-alert:dead-letters:{dead_letters}:{day_key}",
            )
        )
