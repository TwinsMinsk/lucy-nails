"""allow lifecycle-expired entitlement status

Revision ID: 2c9d0e1f2a3b
Revises: 1b8c9d0e1f2a
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op


revision: str = "2c9d0e1f2a3b"
down_revision: Union[str, None] = "1b8c9d0e1f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_entitlements_status",
        "entitlements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_entitlements_status",
        "entitlements",
        "status IN ('active', 'suspended', 'revoked', 'expired')",
    )


def downgrade() -> None:
    # Expiration remains derivable from expires_at, so downgrade can safely
    # map the lifecycle marker back to the pre-migration representation.
    op.execute("UPDATE entitlements SET status = 'active' WHERE status = 'expired'")
    op.drop_constraint(
        "ck_entitlements_status",
        "entitlements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_entitlements_status",
        "entitlements",
        "status IN ('active', 'suspended', 'revoked')",
    )
