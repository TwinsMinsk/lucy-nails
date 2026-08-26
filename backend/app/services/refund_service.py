"""Refund request state machine and access revocation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entitlement import Entitlement
from app.models.purchase import Purchase
from app.models.refund import RefundRequest
from app.services.access_service import AccessService


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
        purchase = await db.get(Purchase, purchase_id)
        if purchase is None:
            raise RefundError("Purchase not found")
        if purchase.payment_status != "success":
            raise RefundError("Only successful purchases can be refunded")

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
        refund: RefundRequest,
        *,
        status: str,
        actor_id: UUID,
        provider_reference: str | None,
        note: str | None,
    ) -> RefundRequest:
        if refund.status in {"processed", "rejected"} and refund.status != status:
            raise RefundError("Completed refund requests cannot be reopened")
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
            entitlement_result = await db.execute(
                select(Entitlement).where(
                    Entitlement.source_purchase_id == refund.purchase_id,
                    Entitlement.status == "active",
                )
            )
            entitlement = entitlement_result.scalar_one_or_none()
            if entitlement is not None:
                await AccessService.revoke_entitlement(
                    db,
                    entitlement,
                    reason=f"Refund processed: {refund.reason}",
                )
        await db.flush()
        return refund

