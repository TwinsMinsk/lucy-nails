"""allow the financial_incident payment event status

The webhook records a second payment for an already paid order as a
``financial_incident`` event, but the check constraint created with the table
did not allow that status, so on a migrated database the insert failed and the
whole notification was rolled back.

Revision ID: a3b4c5d6e7f8
Revises: 9d0e1f2a3b4c
Create Date: 2026-11-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "9d0e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT = "ck_payment_events_processing_status"
# Every status the application writes: "received" while an event is being
# processed, then one terminal status.
NEW_STATUSES = (
    "processing_status IN ('received', 'processed', 'duplicate', 'ignored', "
    "'rejected', 'financial_incident')"
)
OLD_STATUSES = (
    "processing_status IN ('received', 'processed', 'duplicate', 'ignored', 'rejected')"
)


def _constraint_definition() -> str | None:
    return (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = 'payment_events'::regclass AND conname = :name"
            ),
            {"name": CONSTRAINT},
        )
        .scalar()
    )


def upgrade() -> None:
    # Every step is idempotent, so an upgrade interrupted between the two
    # phases finishes when it runs again.
    #
    # Phase 1, inside the migration transaction: swap the constraint for one
    # that is NOT VALID. That needs ACCESS EXCLUSIVE on the table but no scan,
    # so the lock is held only until the transaction commits right below. New
    # rows are checked against the new constraint from here on.
    definition = _constraint_definition()
    if definition is None or "'financial_incident'" not in definition:
        op.execute(
            f"ALTER TABLE payment_events DROP CONSTRAINT IF EXISTS {CONSTRAINT}, "
            f"ADD CONSTRAINT {CONSTRAINT} CHECK ({NEW_STATUSES}) NOT VALID"
        )
    # Phase 2, outside that transaction: VALIDATE takes only SHARE UPDATE
    # EXCLUSIVE, so the webhook keeps reading and writing while existing rows
    # are scanned; repeating it on a validated constraint does nothing.
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TABLE payment_events VALIDATE CONSTRAINT {CONSTRAINT}")
        # Incidents a downgrade parked as rejected (see below) get their
        # status back. No rejection writes the error code
        # duplicate_order_payment: only the incident path does, so this
        # touches nothing else.
        op.execute(
            "UPDATE payment_events SET processing_status = 'financial_incident' "
            "WHERE processing_status = 'rejected' "
            "AND error_code = 'duplicate_order_payment'"
        )


def downgrade() -> None:
    # One transaction. The lock comes first: it lets readers through but holds
    # back every writer, so no webhook can commit a new financial_incident
    # between the UPDATE and the old constraint, which would fail the
    # downgrade.
    op.execute("LOCK TABLE payment_events IN SHARE ROW EXCLUSIVE MODE")
    # The old constraint does not know financial_incident. Such a row records a
    # second payment for an already paid order and must not be lost: it is kept
    # as 'rejected' with its error code duplicate_order_payment unchanged, so
    # the reconciliation views still list it and a new upgrade restores it.
    # No payment event is deleted.
    op.execute(
        "UPDATE payment_events SET processing_status = 'rejected' "
        "WHERE processing_status = 'financial_incident'"
    )
    op.execute(
        f"ALTER TABLE payment_events DROP CONSTRAINT IF EXISTS {CONSTRAINT}, "
        f"ADD CONSTRAINT {CONSTRAINT} CHECK ({OLD_STATUSES})"
    )
