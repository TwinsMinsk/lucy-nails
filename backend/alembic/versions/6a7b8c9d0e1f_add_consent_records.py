"""add offer and personal-data consent records to orders and users

Revision ID: 6a7b8c9d0e1f
Revises: 5f6a7b8c9d0e
Create Date: 2026-09-25

Guest checkout (orders) and self-registration (users) now require two
separate checkboxes: the offer and the personal-data consent (152-FZ as
amended from 01.09.2025). Store when each was given and which version of the
texts was shown. All columns are nullable: historical rows, logged-in
checkouts and admin-created students carry no consent record.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6a7b8c9d0e1f"
down_revision = "5f6a7b8c9d0e"
branch_labels = None
depends_on = None

_TABLES = ("orders", "users")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("offer_accepted_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("personal_data_consent_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("consent_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "consent_version")
        op.drop_column(table, "personal_data_consent_at")
        op.drop_column(table, "offer_accepted_at")
