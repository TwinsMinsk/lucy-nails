"""add runtime operations settings

Revision ID: 1b8c9d0e1f2a
Revises: 0a7b8c9d0e1f
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1b8c9d0e1f2a"
down_revision: Union[str, None] = "0a7b8c9d0e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runtime_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        "ix_runtime_settings_updated_by_id", "runtime_settings", ["updated_by_id"]
    )
    op.execute(
        """
        INSERT INTO permissions (id, name, description)
        VALUES (
            '01000000-0000-0000-0000-000000000012',
            'system.manage_operations',
            'Manage critical operational switches'
        )
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT role_id, '01000000-0000-0000-0000-000000000012'::uuid
        FROM (VALUES
            ('02000000-0000-0000-0000-000000000001'::uuid),
            ('02000000-0000-0000-0000-000000000002'::uuid)
        ) AS allowed(role_id)
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id = "
        "'01000000-0000-0000-0000-000000000012'::uuid"
    )
    op.execute(
        "DELETE FROM permissions WHERE id = "
        "'01000000-0000-0000-0000-000000000012'::uuid"
    )
    op.drop_table("runtime_settings")
