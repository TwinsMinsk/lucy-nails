"""add ad campaigns section with its permissions and marketer role

Revision ID: 9d0e1f2a3b4c
Revises: 8c9d0e1f2a3b
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "9d0e1f2a3b4c"
down_revision: Union[str, None] = "8c9d0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ad_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("groups", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("about", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'active', 'finished')", name="ck_ad_campaigns_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_campaigns_slug", "ad_campaigns", ["slug"], unique=True)

    op.create_table(
        "ad_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("group_key", sa.String(64), nullable=True),
        sa.Column("hook", sa.String(500), nullable=True),
        sa.Column("voiceover", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("utm_content", sa.String(100), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("published_url", sa.String(500), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('reel', 'photo', 'story', 'post', 'other')", name="ck_ad_materials_kind"
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'published')", name="ck_ad_materials_status"
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "code", name="uq_ad_materials_campaign_code"),
    )
    op.create_index("ix_ad_materials_campaign_id", "ad_materials", ["campaign_id"])

    op.create_table(
        "ad_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("variant", sa.String(16), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "role IN ('video', 'cover', 'photo', 'voice', 'other')", name="ck_ad_files_role"
        ),
        sa.ForeignKeyConstraint(["material_id"], ["ad_materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("material_id", "key", name="uq_ad_files_material_key"),
    )
    op.create_index("ix_ad_files_material_id", "ad_files", ["material_id"])
    op.create_index("ix_ad_files_uploaded_by_id", "ad_files", ["uploaded_by_id"])

    op.create_table(
        "ad_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("done_at", sa.DateTime(), nullable=True),
        sa.Column("done_by_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["done_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "key", name="uq_ad_tasks_campaign_key"),
    )
    op.create_index("ix_ad_tasks_campaign_id", "ad_tasks", ["campaign_id"])

    op.create_table(
        "ad_calendar_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("time", sa.String(5), nullable=True),
        sa.Column("week", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("material_id", sa.Uuid(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["ad_materials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "key", name="uq_ad_calendar_campaign_key"),
    )
    op.create_index("ix_ad_calendar_entries_campaign_id", "ad_calendar_entries", ["campaign_id"])

    op.create_table(
        "ad_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["ad_materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_comments_campaign_id", "ad_comments", ["campaign_id"])
    op.create_index("ix_ad_comments_material_id", "ad_comments", ["material_id"])

    op.execute(
        """
        INSERT INTO permissions (id, name, description) VALUES
        ('01000000-0000-0000-0000-000000000014', 'ads.read', 'View and download ad materials'),
        ('01000000-0000-0000-0000-000000000015', 'ads.manage', 'Upload, comment and publish ad materials')
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO roles (id, name, description, is_system, created_at) VALUES
        ('02000000-0000-0000-0000-000000000006', 'marketer', 'Ad campaigns', true, now())
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('owner', 'admin', 'marketer')
          AND p.name IN ('ads.read', 'ads.manage')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (SELECT id FROM permissions WHERE name IN ('ads.read', 'ads.manage'))
        """
    )
    op.execute("DELETE FROM user_role_assignments WHERE role_id IN (SELECT id FROM roles WHERE name = 'marketer')")
    op.execute("DELETE FROM roles WHERE name = 'marketer'")
    op.execute("DELETE FROM permissions WHERE name IN ('ads.read', 'ads.manage')")
    op.drop_index("ix_ad_comments_material_id", table_name="ad_comments")
    op.drop_index("ix_ad_comments_campaign_id", table_name="ad_comments")
    op.drop_table("ad_comments")
    op.drop_index("ix_ad_calendar_entries_campaign_id", table_name="ad_calendar_entries")
    op.drop_table("ad_calendar_entries")
    op.drop_index("ix_ad_tasks_campaign_id", table_name="ad_tasks")
    op.drop_table("ad_tasks")
    op.drop_index("ix_ad_files_uploaded_by_id", table_name="ad_files")
    op.drop_index("ix_ad_files_material_id", table_name="ad_files")
    op.drop_table("ad_files")
    op.drop_index("ix_ad_materials_campaign_id", table_name="ad_materials")
    op.drop_table("ad_materials")
    op.drop_index("ix_ad_campaigns_slug", table_name="ad_campaigns")
    op.drop_table("ad_campaigns")
