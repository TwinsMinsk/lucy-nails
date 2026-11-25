"""record whether an auth session passed MFA

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-11-25

Additive and nullable. Existing rows stay NULL ("unknown"): an account that
requires MFA is refused from such a session only when it has no enabled MFA
credential, so an owner who already uses MFA stays signed in. Sessions that the
old code still issues during a deploy are NULL as well.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("mfa_verified", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("auth_sessions", "mfa_verified")
