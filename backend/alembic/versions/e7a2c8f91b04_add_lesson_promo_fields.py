"""Add promo fields for lesson landing previews

Revision ID: e7a2c8f91b04
Revises: f6e4f3b2a901
Create Date: 2026-05-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7a2c8f91b04"
down_revision: Union[str, None] = "f6e4f3b2a901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column("promo_kinescope_video_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column("promo_poster_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column("promo_description", sa.Text(), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "promo_highlights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("lessons", "promo_highlights")
    op.drop_column("lessons", "promo_description")
    op.drop_column("lessons", "promo_poster_url")
    op.drop_column("lessons", "promo_kinescope_video_id")
