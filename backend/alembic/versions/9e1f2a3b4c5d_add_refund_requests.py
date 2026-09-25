"""add internal refund requests

Revision ID: 9e1f2a3b4c5d
Revises: 8d0e1f2a3b4c
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9e1f2a3b4c5d"
down_revision: Union[str, None] = "8d0e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refund_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purchase_id", sa.Uuid(), nullable=False),
        sa.Column("amount_kopecks", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("processed_by_id", sa.Uuid(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('requested', 'submitted', 'processed', 'rejected')",
            name="ck_refund_requests_status",
        ),
        sa.CheckConstraint("amount_kopecks > 0", name="ck_refund_requests_positive_amount"),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["processed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refund_requests_purchase_id", "refund_requests", ["purchase_id"])
    op.create_index("ix_refund_requests_status", "refund_requests", ["status"])
    op.create_index("ix_refund_requests_provider_reference", "refund_requests", ["provider_reference"])
    op.create_index("ix_refund_requests_created_by_id", "refund_requests", ["created_by_id"])
    op.create_index("ix_refund_requests_processed_by_id", "refund_requests", ["processed_by_id"])


def downgrade() -> None:
    op.drop_index("ix_refund_requests_processed_by_id", table_name="refund_requests")
    op.drop_index("ix_refund_requests_created_by_id", table_name="refund_requests")
    op.drop_index("ix_refund_requests_provider_reference", table_name="refund_requests")
    op.drop_index("ix_refund_requests_status", table_name="refund_requests")
    op.drop_index("ix_refund_requests_purchase_id", table_name="refund_requests")
    op.drop_table("refund_requests")
