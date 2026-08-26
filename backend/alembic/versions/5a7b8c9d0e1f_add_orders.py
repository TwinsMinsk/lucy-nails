"""add immutable checkout orders

Revision ID: 5a7b8c9d0e1f
Revises: 3d5067c10861
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5a7b8c9d0e1f"
down_revision: Union[str, None] = "3d5067c10861"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("tariff", sa.String(20), nullable=False),
        sa.Column("customer_email", sa.String(320), nullable=False),
        sa.Column("customer_phone", sa.String(64), nullable=True),
        sa.Column("amount_kopecks", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("access_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("status_token_hash", sa.String(64), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_course_id", "orders", ["course_id"])
    op.create_index("ix_orders_customer_email", "orders", ["customer_email"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.add_column("purchases", sa.Column("order_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_purchases_order_id_orders",
        "purchases",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_purchases_order_id", "purchases", ["order_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_purchases_order_id", table_name="purchases")
    op.drop_constraint("fk_purchases_order_id_orders", "purchases", type_="foreignkey")
    op.drop_column("purchases", "order_id")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_customer_email", table_name="orders")
    op.drop_index("ix_orders_course_id", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
