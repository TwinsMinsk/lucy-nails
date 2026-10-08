"""Record mailbox ownership without trusting historical registrations.

Revision ID: 7b8c9d0e1f2a
Revises: 6a7b8c9d0e1f
"""

from alembic import op
import sqlalchemy as sa

revision = "7b8c9d0e1f2a"
down_revision = "6a7b8c9d0e1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "email_verified_at")
