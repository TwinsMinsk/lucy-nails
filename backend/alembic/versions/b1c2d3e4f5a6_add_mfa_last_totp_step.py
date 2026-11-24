"""remember the last accepted TOTP step to refuse replayed codes

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-11-25

Additive and nullable: code that does not know the column keeps working.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mfa_credentials",
        sa.Column("last_totp_step", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mfa_credentials", "last_totp_step")
