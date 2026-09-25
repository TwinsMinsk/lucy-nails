"""add sanitized payment event journal

Revision ID: 8d0e1f2a3b4c
Revises: 7c9d0e1f2a3b
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8d0e1f2a3b4c"
down_revision: Union[str, None] = "7c9d0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("external_event_id", sa.String(255), nullable=True),
        sa.Column("order_reference", sa.String(255), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("purchase_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False),
        sa.Column("amount_kopecks", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("sanitized_payload", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "processing_status IN ('received', 'processed', 'duplicate', 'ignored', 'rejected')",
            name="ck_payment_events_processing_status",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_events_event_hash", "payment_events", ["event_hash"], unique=True)
    op.create_index("ix_payment_events_external_event_id", "payment_events", ["external_event_id"])
    op.create_index("ix_payment_events_order_reference", "payment_events", ["order_reference"])
    op.create_index("ix_payment_events_order_id", "payment_events", ["order_id"])
    op.create_index("ix_payment_events_purchase_id", "payment_events", ["purchase_id"])
    op.create_index("ix_payment_events_processing_status", "payment_events", ["processing_status"])
    op.create_index("ix_payment_events_error_code", "payment_events", ["error_code"])


def downgrade() -> None:
    op.drop_index("ix_payment_events_error_code", table_name="payment_events")
    op.drop_index("ix_payment_events_processing_status", table_name="payment_events")
    op.drop_index("ix_payment_events_purchase_id", table_name="payment_events")
    op.drop_index("ix_payment_events_order_id", table_name="payment_events")
    op.drop_index("ix_payment_events_order_reference", table_name="payment_events")
    op.drop_index("ix_payment_events_external_event_id", table_name="payment_events")
    op.drop_index("ix_payment_events_event_hash", table_name="payment_events")
    op.drop_table("payment_events")
