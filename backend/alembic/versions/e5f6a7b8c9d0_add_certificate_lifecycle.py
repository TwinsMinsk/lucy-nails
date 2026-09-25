"""add certificate lifecycle fields

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "certificates",
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
    )
    op.add_column("certificates", sa.Column("revoked_at", sa.DateTime(), nullable=True))
    op.add_column("certificates", sa.Column("revoked_by_id", sa.Uuid(), nullable=True))
    op.add_column("certificates", sa.Column("revoke_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_certificates_revoked_by_id_users",
        "certificates",
        "users",
        ["revoked_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_certificates_status", "certificates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_certificates_status", table_name="certificates")
    op.drop_constraint(
        "fk_certificates_revoked_by_id_users", "certificates", type_="foreignkey"
    )
    op.drop_column("certificates", "revoke_reason")
    op.drop_column("certificates", "revoked_by_id")
    op.drop_column("certificates", "revoked_at")
    op.drop_column("certificates", "status")
