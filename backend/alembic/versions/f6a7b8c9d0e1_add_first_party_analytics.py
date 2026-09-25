"""add first-party analytics and order attribution snapshots

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTM_PARTS = ("source", "medium", "campaign", "content", "term")


def upgrade() -> None:
    op.add_column("orders", sa.Column("course_title", sa.String(length=255), nullable=True))
    op.execute(
        """
        UPDATE orders
        SET course_title = courses.title
        FROM courses
        WHERE orders.course_id = courses.id
        """
    )
    op.execute("UPDATE orders SET course_title = 'Course' WHERE course_title IS NULL")
    op.alter_column("orders", "course_title", nullable=False)
    for touch in ("first", "last"):
        for part in UTM_PARTS:
            op.add_column(
                "orders",
                sa.Column(f"{touch}_utm_{part}", sa.String(length=255), nullable=True),
            )
    op.create_index("ix_orders_first_utm_source", "orders", ["first_utm_source"])
    op.create_index("ix_orders_last_utm_source", "orders", ["last_utm_source"])

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("happened_at", sa.DateTime(), nullable=False),
        sa.Column("anonymous_id", sa.String(length=128), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("course_id", sa.Uuid(), nullable=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=True),
        sa.Column("utm_source", sa.String(length=255), nullable=True),
        sa.Column("utm_medium", sa.String(length=255), nullable=True),
        sa.Column("utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("utm_content", sa.String(length=255), nullable=True),
        sa.Column("utm_term", sa.String(length=255), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    for column in (
        "event_id",
        "event_name",
        "source",
        "happened_at",
        "anonymous_id",
        "user_id",
        "order_id",
        "course_id",
        "lesson_id",
        "utm_source",
    ):
        op.create_index(f"ix_analytics_events_{column}", "analytics_events", [column])


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_index("ix_orders_last_utm_source", table_name="orders")
    op.drop_index("ix_orders_first_utm_source", table_name="orders")
    for touch in ("last", "first"):
        for part in reversed(UTM_PARTS):
            op.drop_column("orders", f"{touch}_utm_{part}")
    op.drop_column("orders", "course_title")
