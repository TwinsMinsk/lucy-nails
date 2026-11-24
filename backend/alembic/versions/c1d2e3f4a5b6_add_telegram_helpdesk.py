"""add telegram help desk: processed updates, customer threads, message map

Revision ID: c1d2e3f4a5b6
Revises: c2d3e4f5a6b7
Create Date: 2026-11-25 00:05:46.273279

Additive only. Message text and files are not stored: the operators' Telegram
group is the record of the conversation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_updates",
        sa.Column("update_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("update_id"),
    )
    op.create_index(
        op.f("ix_telegram_updates_received_at"), "telegram_updates", ["received_at"], unique=False
    )
    op.create_table(
        "helpdesk_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("stated_email", sa.String(length=320), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("topic_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("last_customer_message_at", sa.DateTime(), nullable=True),
        sa.Column("last_operator_message_at", sa.DateTime(), nullable=True),
        sa.Column("last_ack_at", sa.DateTime(), nullable=True),
        sa.Column("flood_notice_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", "topic_id", name="uq_helpdesk_threads_chat_topic"),
        sa.UniqueConstraint("telegram_user_id"),
    )
    op.create_index(
        op.f("ix_helpdesk_threads_user_id"), "helpdesk_threads", ["user_id"], unique=False
    )
    op.create_table(
        "helpdesk_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("customer_message_id", sa.BigInteger(), nullable=True),
        sa.Column("group_message_id", sa.BigInteger(), nullable=True),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["helpdesk_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "thread_id", "direction", "customer_message_id",
            name="uq_helpdesk_messages_customer_side",
        ),
        sa.UniqueConstraint(
            "thread_id", "direction", "group_message_id",
            name="uq_helpdesk_messages_group_side",
        ),
    )
    op.create_index(
        "ix_helpdesk_messages_thread_created",
        "helpdesk_messages",
        ["thread_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_helpdesk_messages_thread_created", table_name="helpdesk_messages")
    op.drop_table("helpdesk_messages")
    op.drop_index(op.f("ix_helpdesk_threads_user_id"), table_name="helpdesk_threads")
    op.drop_table("helpdesk_threads")
    op.drop_index(op.f("ix_telegram_updates_received_at"), table_name="telegram_updates")
    op.drop_table("telegram_updates")
