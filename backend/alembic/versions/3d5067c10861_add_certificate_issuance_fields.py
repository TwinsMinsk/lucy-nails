"""add_certificate_issuance_fields

Revision ID: 3d5067c10861
Revises: d4e5f6a7b8c9
Create Date: 2026-07-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3d5067c10861"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(255), nullable=True))
    op.add_column(
        "certificates",
        sa.Column("student_name", sa.String(255), nullable=False, server_default=""),
    )
    op.alter_column("certificates", "student_name", server_default=None)
    op.add_column("certificates", sa.Column("png_url", sa.String(512), nullable=True))
    op.create_unique_constraint(
        "uq_certificates_user_course", "certificates", ["user_id", "course_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_certificates_user_course", "certificates", type_="unique")
    op.drop_column("certificates", "png_url")
    op.drop_column("certificates", "student_name")
    op.drop_column("users", "full_name")
