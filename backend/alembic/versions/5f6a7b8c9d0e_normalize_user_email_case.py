"""normalize user email case and enforce case-insensitive uniqueness

Revision ID: 5f6a7b8c9d0e
Revises: 4e9d0e1f2a3b
Create Date: 2026-09-25

Auth compared User.email case-sensitively on register/login while the
Prodamus webhook and forgot-password already lowercased it. A device that
auto-capitalises an email (e.g. iPhone) could then get "Incorrect email or
password" on an account created by payment, and case variants could create
duplicate accounts. This migration lowercases all stored emails and adds a
unique functional index on lower(email) so the DB enforces case-insensitive
uniqueness going forward.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5f6a7b8c9d0e"
down_revision: Union[str, None] = "4e9d0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    duplicates = conn.execute(
        sa.text(
            """
            SELECT lower(email) AS email, count(*) AS cnt
            FROM users
            GROUP BY lower(email)
            HAVING count(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        emails = ", ".join(row.email for row in duplicates)
        raise RuntimeError(
            "Cannot normalize user emails: case-variant duplicate accounts exist for "
            f"{emails}. Merge these accounts manually, then re-run this migration."
        )

    conn.execute(sa.text("UPDATE users SET email = lower(email) WHERE email <> lower(email)"))

    op.create_index(
        "ix_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_email_lower", table_name="users")
