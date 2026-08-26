"""add course entitlements and configurable access duration

Revision ID: 7c9d0e1f2a3b
Revises: 6b8c9d0e1f2a
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c9d0e1f2a3b"
down_revision: Union[str, None] = "6b8c9d0e1f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("access_days", sa.Integer(), server_default="30", nullable=False),
    )
    op.create_table(
        "entitlements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("source_purchase_id", sa.Uuid(), nullable=True),
        sa.Column("granted_by_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("tariff", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("source IN ('purchase', 'manual')", name="ck_entitlements_source"),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'revoked')",
            name="ck_entitlements_status",
        ),
        sa.CheckConstraint("tariff IN ('self', 'support')", name="ck_entitlements_tariff"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_purchase_id"], ["purchases.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["granted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entitlements_user_id", "entitlements", ["user_id"])
    op.create_index("ix_entitlements_course_id", "entitlements", ["course_id"])
    op.create_index("ix_entitlements_granted_by_id", "entitlements", ["granted_by_id"])
    op.create_index("ix_entitlements_status", "entitlements", ["status"])
    op.create_index("ix_entitlements_expires_at", "entitlements", ["expires_at"])
    op.create_index(
        "ix_entitlements_source_purchase_id",
        "entitlements",
        ["source_purchase_id"],
        unique=True,
    )

    # Existing successful purchases become access grants without modifying
    # the immutable financial history. Historical admin_grant_* rows are
    # explicitly marked as legacy manual grants for later reconciliation.
    op.execute(
        """
        INSERT INTO entitlements (
            id, user_id, course_id, source_purchase_id, granted_by_id,
            source, tariff, status, starts_at, expires_at, reason,
            revoked_at, created_at, updated_at
        )
        SELECT
            gen_random_uuid(), p.user_id, p.course_id, p.id, NULL,
            CASE WHEN p.payment_id LIKE 'admin_grant_%' THEN 'manual' ELSE 'purchase' END,
            p.tariff::text, 'active', COALESCE(p.paid_at, p.created_at), p.expires_at,
            CASE WHEN p.payment_id LIKE 'admin_grant_%'
                 THEN 'Imported legacy admin grant'
                 ELSE NULL END,
            NULL, p.created_at, p.created_at
        FROM purchases p
        WHERE p.payment_status = 'success'
        ON CONFLICT (source_purchase_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_entitlements_source_purchase_id", table_name="entitlements")
    op.drop_index("ix_entitlements_expires_at", table_name="entitlements")
    op.drop_index("ix_entitlements_status", table_name="entitlements")
    op.drop_index("ix_entitlements_granted_by_id", table_name="entitlements")
    op.drop_index("ix_entitlements_course_id", table_name="entitlements")
    op.drop_index("ix_entitlements_user_id", table_name="entitlements")
    op.drop_table("entitlements")
    op.drop_column("courses", "access_days")
