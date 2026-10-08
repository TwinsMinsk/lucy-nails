"""Refund request state machine and access revocation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entitlement import Entitlement
from app.models.certificate import Certificate
from app.models.purchase import Purchase, paid_financial_filter
from app.models.refund import RefundRequest
from app.services.access_service import AccessService
from app.services.analytics_service import AnalyticsService


class RefundError(ValueError):
    pass


class RefundService:
    @staticmethod
    async def list_refunds(db: AsyncSession) -> list[RefundRequest]:
        result = await db.execute(
            select(RefundRequest)
            .options(selectinload(RefundRequest.purchase))
            .order_by(RefundRequest.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_refund(
        db: AsyncSession,
        *,
        purchase_id: UUID,
        amount_kopecks: int,
        reason: str,
        created_by_id: UUID,
    ) -> RefundRequest:
        purchase = await db.scalar(
            select(Purchase)
            .where(Purchase.id == purchase_id)
            .with_for_update()
        )
        if purchase is None:
            raise RefundError("Purchase not found")
        if purchase.payment_status != "success":
            raise RefundError("Only successful purchases can be refunded")
        if await db.scalar(select(Purchase.id).where(Purchase.id == purchase.id, paid_financial_filter())) is None:
            raise RefundError("Only a paid financial purchase can be refunded")

        allocated = await db.scalar(
            select(func.coalesce(func.sum(RefundRequest.amount_kopecks), 0)).where(
                RefundRequest.purchase_id == purchase_id,
                RefundRequest.status != "rejected",
            )
        )
        if amount_kopecks + int(allocated or 0) > purchase.amount_kopecks:
            raise RefundError("Refund amount exceeds the remaining paid amount")

        refund = RefundRequest(
            purchase_id=purchase_id,
            amount_kopecks=amount_kopecks,
            reason=reason.strip(),
            status="requested",
            created_by_id=created_by_id,
        )
        db.add(refund)
        await db.flush()
        return refund

    @staticmethod
    async def update_refund(
        db: AsyncSession,
        refund_id: UUID,
        *,
        status: str,
        actor_id: UUID,
        provider_reference: str | None,
        note: str | None,
    ) -> tuple[RefundRequest, dict[str, str | None]]:
        refund = await db.scalar(
            select(RefundRequest)
            .where(RefundRequest.id == refund_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if refund is None:
            raise RefundError("Refund request not found")
        old_value = {
            "status": refund.status,
            "provider_reference": refund.provider_reference,
            "note": refund.note,
        }
        previous_status = refund.status
        if provider_reference is not None and not provider_reference.strip():
            raise RefundError("Provider reference cannot be blank")
        if refund.status in {"processed", "rejected"} and refund.status != status:
            raise RefundError("Completed refund requests cannot be reopened")
        if refund.status in {"processed", "rejected"}:
            return refund, old_value
        allowed = {
            "requested": {"requested", "submitted", "processed", "rejected"},
            "submitted": {"submitted", "processed", "rejected"},
            "processed": {"processed"},
            "rejected": {"rejected"},
        }
        if status not in allowed.get(refund.status, set()):
            raise RefundError("Invalid refund status transition")
        if status == "processed" and not (provider_reference or refund.provider_reference):
            raise RefundError("Provider reference is required for a processed refund")

        refund.status = status
        if provider_reference is not None:
            refund.provider_reference = provider_reference.strip()
        if note is not None:
            refund.note = note.strip()

        if status in {"processed", "rejected"}:
            refund.processed_by_id = actor_id
            refund.processed_at = datetime.utcnow()

        if status == "processed":
            purchase = await db.scalar(
                select(Purchase)
                .where(Purchase.id == refund.purchase_id)
                .with_for_update()
            )
            await db.flush()
            processed_total = await db.scalar(
                select(func.coalesce(func.sum(RefundRequest.amount_kopecks), 0)).where(
                    RefundRequest.purchase_id == refund.purchase_id,
                    RefundRequest.status == "processed",
                )
            )
            if purchase is not None and int(processed_total or 0) >= purchase.amount_kopecks:
                entitlement_result = await db.execute(
                    select(Entitlement).where(
                        Entitlement.source_purchase_id == refund.purchase_id,
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                entitlement = entitlement_result.scalar_one_or_none()
                if entitlement is None:
                    entitlement = AccessService.create_purchase_entitlement(purchase)
                    db.add(entitlement)
                    await db.flush()
                if entitlement.status != "revoked":
                    await AccessService.revoke_entitlement(
                        db,
                        entitlement,
                        reason=f"Refund processed: {refund.reason}",
                    )
                certificates = await db.scalars(select(Certificate).where(
                    Certificate.user_id == purchase.user_id,
                    Certificate.course_id == purchase.course_id,
                    Certificate.status != "revoked",
                ).with_for_update())
                for certificate in certificates:
                    certificate.status = "revoked"
                    certificate.revoked_at = datetime.utcnow()
                    certificate.revoked_by_id = actor_id
                    certificate.revoke_reason = f"Refund processed: {refund.reason}"
            if previous_status != "processed" and purchase is not None:
                await AnalyticsService.record_event(
                    db,
                    event_id=f"refund_processed:{refund.id}",
                    event_name="refund_processed",
                    source="server",
                    user_id=purchase.user_id,
                    order_id=purchase.order_id,
                    course_id=purchase.course_id,
                    properties={},
                )
        await db.flush()
        return refund, old_value
