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

from alembic import op


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "9d0e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every status the application writes: "received" while an event is being
# processed, then one terminal status.
NEW_STATUSES = (
    "processing_status IN ('received', 'processed', 'duplicate', 'ignored', "
    "'rejected', 'financial_incident')"
)
OLD_STATUSES = (
    "processing_status IN ('received', 'processed', 'duplicate', 'ignored', 'rejected')"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_payment_events_processing_status", "payment_events", type_="check"
    )
    op.create_check_constraint(
        "ck_payment_events_processing_status", "payment_events", NEW_STATUSES
    )
    # Incidents a downgrade parked as rejected (see below) get their status
    # back. No rejection writes the error code duplicate_order_payment: only the
    # incident path does, so this touches nothing else.
    op.execute(
        "UPDATE payment_events SET processing_status = 'financial_incident' "
        "WHERE processing_status = 'rejected' AND error_code = 'duplicate_order_payment'"
    )


def downgrade() -> None:
    # The old constraint does not know financial_incident. Such a row records a
    # second payment for an already paid order and must not be lost: it is kept
    # as 'rejected' with its error code duplicate_order_payment unchanged, so
    # the reconciliation views still list it and a new upgrade restores it.
    # No payment event is deleted.
    op.execute(
        "UPDATE payment_events SET processing_status = 'rejected' "
        "WHERE processing_status = 'financial_incident'"
    )
    op.drop_constraint(
        "ck_payment_events_processing_status", "payment_events", type_="check"
    )
    op.create_check_constraint(
        "ck_payment_events_processing_status", "payment_events", OLD_STATUSES
    )
