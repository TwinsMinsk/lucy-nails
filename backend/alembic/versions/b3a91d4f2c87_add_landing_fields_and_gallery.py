"""Add landing fields to courses/modules and gallery_items table

Revision ID: b3a91d4f2c87
Revises: e7a2c8f91b04
Create Date: 2026-05-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3a91d4f2c87"
down_revision: Union[str, None] = "e7a2c8f91b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # courses: hero copy overrides
    op.add_column("courses", sa.Column("landing_title", sa.String(length=255), nullable=True))
    op.add_column("courses", sa.Column("landing_subtitle", sa.String(length=500), nullable=True))
    op.add_column("courses", sa.Column("landing_description", sa.Text(), nullable=True))
    op.add_column("courses", sa.Column("landing_audience", sa.Text(), nullable=True))
    op.add_column("courses", sa.Column("landing_support_note", sa.Text(), nullable=True))
    op.add_column(
        "courses",
        sa.Column("landing_hero_stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "courses",
        sa.Column("landing_benefits", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "courses",
        sa.Column("landing_instructor_image_url", sa.String(length=500), nullable=True),
    )

    # modules: landing copy overrides
    op.add_column("modules", sa.Column("landing_description", sa.Text(), nullable=True))
    op.add_column("modules", sa.Column("landing_outcome", sa.Text(), nullable=True))
    op.add_column(
        "modules",
        sa.Column("landing_bullets", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "modules",
        sa.Column("landing_mistakes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("modules", sa.Column("landing_duration_label", sa.String(length=32), nullable=True))

    # gallery_items: global gallery for the landing page
    op.create_table(
        "gallery_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("alt", sa.String(length=255), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_gallery_items_order_index",
        "gallery_items",
        ["order_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_gallery_items_order_index", table_name="gallery_items")
    op.drop_table("gallery_items")

    op.drop_column("modules", "landing_duration_label")
    op.drop_column("modules", "landing_mistakes")
    op.drop_column("modules", "landing_bullets")
    op.drop_column("modules", "landing_outcome")
    op.drop_column("modules", "landing_description")

    op.drop_column("courses", "landing_instructor_image_url")
    op.drop_column("courses", "landing_benefits")
    op.drop_column("courses", "landing_hero_stats")
    op.drop_column("courses", "landing_support_note")
    op.drop_column("courses", "landing_audience")
    op.drop_column("courses", "landing_description")
    op.drop_column("courses", "landing_subtitle")
    op.drop_column("courses", "landing_title")
