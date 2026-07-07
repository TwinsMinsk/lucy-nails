"""add token_version to users

Revision ID: d4e5f6a7b8c9
Revises: b3a91d4f2c87
Create Date: 2026-07-07

Adds users.token_version — a monotonic counter bumped on every password
change/reset. JWTs embed it as "ver"; a token whose "ver" != the stored value
is rejected, so a password change invalidates all previously issued tokens.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "b3a91d4f2c87"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
