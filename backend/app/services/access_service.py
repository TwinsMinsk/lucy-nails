"""Canonical course-access operations."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course
from app.models.entitlement import Entitlement
from app.models.module import Module
from app.models.purchase import Purchase
from app.models.outbox import OutboxMessage
from app.models.user import User
from app.core.config import settings
from app.services.outbox_service import enqueue_outbox_message
from app.services.support_access_service import has_active_support_entitlement


@dataclass(frozen=True)
class ActiveCourseAccess:
    course: Course
    tariff: str
    expires_at: datetime


class AccessService:
    """Use entitlements as the source of truth, with a temporary legacy fallback."""

    @staticmethod
    async def get_active_entitlement(
        db: AsyncSession,
        user_id: UUID,
        course_id: UUID,
        *,
        now: datetime | None = None,
    ) -> Entitlement | None:
        current_time = now or datetime.utcnow()
        result = await db.execute(
            select(Entitlement)
            .where(
                Entitlement.user_id == user_id,
                Entitlement.course_id == course_id,
                Entitlement.status == "active",
                Entitlement.starts_at <= current_time,
                Entitlement.expires_at > current_time,
            )
            .order_by(Entitlement.expires_at.desc(), Entitlement.created_at.desc())
        )
        return result.scalars().first()

    @staticmethod
    async def has_active_access(
        db: AsyncSession,
        user_id: UUID,
        course_id: UUID,
        *,
        now: datetime | None = None,
    ) -> bool:
        current_time = now or datetime.utcnow()
        entitlement = await AccessService.get_active_entitlement(
            db, user_id, course_id, now=current_time
        )
        if entitlement is not None:
            return True

        entitlement_exists = await db.scalar(
            select(Entitlement.id)
            .where(
                Entitlement.user_id == user_id,
                Entitlement.course_id == course_id,
            )
            .limit(1)
        )
        if entitlement_exists is not None:
            # Once a pair has entered the entitlement model, its state is
            # authoritative. An immutable successful purchase must never
            # resurrect revoked, suspended, or expired access.
            return False

        # Compatibility window for records created before the entitlement
        # migration or while rolling out across multiple application instances.
        legacy_result = await db.execute(
            select(Purchase.id)
            .where(
                Purchase.user_id == user_id,
                Purchase.course_id == course_id,
                Purchase.payment_status == "success",
                Purchase.expires_at > current_time,
            )
            .limit(1)
        )
        return legacy_result.scalar_one_or_none() is not None

    @staticmethod
    def create_purchase_entitlement(purchase: Purchase) -> Entitlement:
        if purchase.id is None:
            raise ValueError("Purchase must be flushed before creating its entitlement")
        return Entitlement(
            user_id=purchase.user_id,
            course_id=purchase.course_id,
            source_purchase_id=purchase.id,
            source="purchase",
            tariff=purchase.tariff,
            status="active",
            starts_at=purchase.paid_at or purchase.created_at or datetime.utcnow(),
            expires_at=purchase.expires_at,
        )

    @staticmethod
    async def _enqueue_support_group_action(
        db: AsyncSession,
        entitlement: Entitlement,
        *,
        kind: str,
        dedupe_suffix: str,
    ) -> bool:
        if (
            entitlement.tariff != "support"
            or not settings.TELEGRAM_BOT_TOKEN
            or settings.TELEGRAM_SUPPORT_GROUP_ID is None
        ):
            return False
        if kind == "telegram_group_remove" and await has_active_support_entitlement(
            db,
            entitlement.user_id,
            exclude_entitlement_id=entitlement.id,
        ):
            return False
        telegram_id = await db.scalar(
            select(User.telegram_id).where(User.id == entitlement.user_id)
        )
        if telegram_id is None:
            return False
        dedupe_key = f"entitlement:{entitlement.id}:{dedupe_suffix}"
        if await db.scalar(
            select(OutboxMessage.id).where(OutboxMessage.dedupe_key == dedupe_key)
        ) is not None:
            return False
        enqueue_outbox_message(
            db,
            kind=kind,
            channel="telegram",
            recipient=str(telegram_id),
            payload={
                "group_id": settings.TELEGRAM_SUPPORT_GROUP_ID,
                "user_id": str(entitlement.user_id),
            },
            dedupe_key=dedupe_key,
        )
        return True

    @staticmethod
    async def enqueue_support_group_restore(
        db: AsyncSession,
        entitlement: Entitlement,
    ) -> bool:
        return await AccessService._enqueue_support_group_action(
            db,
            entitlement,
            kind="telegram_group_restore",
            dedupe_suffix="group-restore",
        )

    @staticmethod
    async def enqueue_support_group_removal(
        db: AsyncSession,
        entitlement: Entitlement,
        *,
        dedupe_suffix: str,
    ) -> bool:
        return await AccessService._enqueue_support_group_action(
            db,
            entitlement,
            kind="telegram_group_remove",
            dedupe_suffix=dedupe_suffix,
        )

    @staticmethod
    async def grant_manual_access(
        db: AsyncSession,
        *,
        user_id: UUID,
        course_id: UUID,
        tariff: str,
        access_days: int,
        granted_by_id: UUID,
        reason: str,
    ) -> Entitlement:
        now = datetime.utcnow()
        current = await AccessService.get_active_entitlement(db, user_id, course_id, now=now)
        extension_base = max(now, current.expires_at) if current else now
        entitlement = Entitlement(
            user_id=user_id,
            course_id=course_id,
            granted_by_id=granted_by_id,
            source="manual",
            tariff=tariff,
            status="active",
            starts_at=now,
            expires_at=extension_base + timedelta(days=access_days),
            reason=reason.strip(),
        )
        db.add(entitlement)
        await db.flush()
        await AccessService.enqueue_support_group_restore(db, entitlement)
        return entitlement

    @staticmethod
    async def revoke_entitlement(
        db: AsyncSession,
        entitlement: Entitlement,
        *,
        reason: str,
    ) -> None:
        entitlement.status = "revoked"
        entitlement.revoked_at = datetime.utcnow()
        entitlement.reason = reason.strip()
        await AccessService.enqueue_support_group_removal(
            db,
            entitlement,
            dedupe_suffix="group-remove:revoked",
        )
        await db.flush()

    @staticmethod
    async def extend_entitlement(
        db: AsyncSession,
        entitlement: Entitlement,
        *,
        days: int,
        reason: str,
    ) -> None:
        if entitlement.status == "revoked":
            raise ValueError("Revoked access cannot be extended")
        now = datetime.utcnow()
        entitlement.expires_at = max(now, entitlement.expires_at) + timedelta(days=days)
        if entitlement.status == "expired":
            entitlement.status = "active"
            entitlement.revoked_at = None
            await AccessService.enqueue_support_group_restore(db, entitlement)
        entitlement.reason = reason.strip()
        await db.flush()

    @staticmethod
    async def suspend_entitlement(
        db: AsyncSession,
        entitlement: Entitlement,
        *,
        reason: str,
    ) -> None:
        if entitlement.status != "active":
            raise ValueError("Only active access can be suspended")
        entitlement.status = "suspended"
        entitlement.reason = reason.strip()
        await AccessService.enqueue_support_group_removal(
            db,
            entitlement,
            dedupe_suffix="group-remove:suspended",
        )
        await db.flush()

    @staticmethod
    async def restore_entitlement(
        db: AsyncSession,
        entitlement: Entitlement,
        *,
        reason: str,
    ) -> None:
        if entitlement.status != "suspended":
            raise ValueError("Only suspended access can be restored")
        if entitlement.expires_at <= datetime.utcnow():
            raise ValueError("Extend expired access before restoring it")
        entitlement.status = "active"
        entitlement.reason = reason.strip()
        entitlement.revoked_at = None
        await AccessService._enqueue_support_group_action(
            db,
            entitlement,
            kind="telegram_group_restore",
            dedupe_suffix="group-restore:resumed",
        )
        await db.flush()

    @staticmethod
    async def get_active_course_accesses(
        db: AsyncSession,
        user_id: UUID,
    ) -> list[ActiveCourseAccess]:
        now = datetime.utcnow()
        entitlement_result = await db.execute(
            select(Entitlement)
            .where(
                Entitlement.user_id == user_id,
                Entitlement.status == "active",
                Entitlement.starts_at <= now,
                Entitlement.expires_at > now,
            )
            .options(
                selectinload(Entitlement.course)
                .selectinload(Course.modules)
                .selectinload(Module.lessons)
            )
            .order_by(Entitlement.expires_at.desc(), Entitlement.created_at.desc())
        )
        entitlements = entitlement_result.scalars().all()

        by_course: dict[UUID, ActiveCourseAccess] = {}
        for entitlement in entitlements:
            if entitlement.course and entitlement.course_id not in by_course:
                by_course[entitlement.course_id] = ActiveCourseAccess(
                    course=entitlement.course,
                    tariff=entitlement.tariff,
                    expires_at=entitlement.expires_at,
                )

        entitlement_course_ids = set(
            (
                await db.execute(
                    select(Entitlement.course_id).where(
                        Entitlement.user_id == user_id
                    )
                )
            )
            .scalars()
            .all()
        )
        legacy_result = await db.execute(
            select(Purchase)
            .where(
                and_(
                    Purchase.user_id == user_id,
                    Purchase.payment_status == "success",
                    Purchase.expires_at > now,
                )
            )
            .options(
                selectinload(Purchase.course)
                .selectinload(Course.modules)
                .selectinload(Module.lessons)
            )
            .order_by(Purchase.expires_at.desc(), Purchase.created_at.desc())
        )
        for purchase in legacy_result.scalars().all():
            if (
                purchase.course
                and purchase.course_id not in entitlement_course_ids
                and purchase.course_id not in by_course
            ):
                by_course[purchase.course_id] = ActiveCourseAccess(
                    course=purchase.course,
                    tariff=purchase.tariff,
                    expires_at=purchase.expires_at,
                )

        return sorted(by_course.values(), key=lambda item: item.expires_at, reverse=True)
