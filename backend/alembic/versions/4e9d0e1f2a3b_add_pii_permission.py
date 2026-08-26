"""add explicit permission for unmasked personal data

Revision ID: 4e9d0e1f2a3b
Revises: 3d9d0e1f2a3b
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op


revision: str = "4e9d0e1f2a3b"
down_revision: Union[str, None] = "3d9d0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (id, name, description)
        VALUES (
            '01000000-0000-0000-0000-000000000013',
            'pii.read',
            'Read unmasked personal data'
        )
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('owner', 'admin', 'curator')
          AND p.name = 'pii.read'
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
            SELECT id FROM permissions WHERE name = 'pii.read'
        )
        """
    )
    op.execute("DELETE FROM permissions WHERE name = 'pii.read'")
