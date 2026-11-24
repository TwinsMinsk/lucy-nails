"""add commerce.manage_pricing permission for course prices and access duration

Revision ID: a0b1c2d3e4f5
Revises: 9d0e1f2a3b4c
Create Date: 2026-11-25

Data-only: content.manage no longer changes commercial terms. Only the owner
and admin roles receive the new permission; content managers keep editing the
rest of the course.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "9d0e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (id, name, description) VALUES
        ('01000000-0000-0000-0000-000000000016', 'commerce.manage_pricing',
         'Change course prices and access duration')
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('owner', 'admin')
          AND p.name = 'commerce.manage_pricing'
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (SELECT id FROM permissions WHERE name = 'commerce.manage_pricing')
        """
    )
    op.execute("DELETE FROM permissions WHERE name = 'commerce.manage_pricing'")
