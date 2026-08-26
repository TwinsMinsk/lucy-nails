"""invalidate privileged tokens after session-bound MFA rollout

Revision ID: 3d9d0e1f2a3b
Revises: 2c9d0e1f2a3b
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op


revision: str = "3d9d0e1f2a3b"
down_revision: Union[str, None] = "2c9d0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users u
        SET token_version = u.token_version + 1
        WHERE EXISTS (
            SELECT 1
            FROM user_role_assignments ura
            JOIN roles r ON r.id = ura.role_id
            WHERE ura.user_id = u.id
              AND r.name IN ('owner', 'admin')
        )
        """
    )
    op.execute(
        """
        UPDATE auth_sessions s
        SET revoked_at = NOW()
        WHERE s.revoked_at IS NULL
          AND EXISTS (
              SELECT 1
              FROM user_role_assignments ura
              JOIN roles r ON r.id = ura.role_id
              WHERE ura.user_id = s.user_id
                AND r.name IN ('owner', 'admin')
          )
        """
    )


def downgrade() -> None:
    # Token invalidation is deliberately irreversible: restoring previously
    # valid credentials would weaken security during rollback.
    pass
