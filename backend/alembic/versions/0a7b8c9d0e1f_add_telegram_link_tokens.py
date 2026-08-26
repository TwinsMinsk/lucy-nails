"""add one-time Telegram link tokens

Revision ID: 0a7b8c9d0e1f
Revises: f6a7b8c9d0e1
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0a7b8c9d0e1f"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_link_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_telegram_link_tokens_user_id", "telegram_link_tokens", ["user_id"]
    )
    op.create_index(
        "ix_telegram_link_tokens_token_hash",
        "telegram_link_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_telegram_link_tokens_expires_at", "telegram_link_tokens", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_table("telegram_link_tokens")
