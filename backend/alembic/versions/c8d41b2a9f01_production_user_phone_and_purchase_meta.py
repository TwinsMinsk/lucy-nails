"""Production: user phone, purchase paid_at and customer_phone

Revision ID: c8d41b2a9f01
Revises: 2f3f813eeb34
Create Date: 2026-05-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d41b2a9f01"
down_revision: Union[str, None] = "2f3f813eeb34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=64), nullable=True))
    op.create_index("ix_users_phone", "users", ["phone"], unique=False)
    op.add_column("purchases", sa.Column("paid_at", sa.DateTime(), nullable=True))
    op.add_column("purchases", sa.Column("customer_phone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("purchases", "customer_phone")
    op.drop_column("purchases", "paid_at")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_column("users", "phone")
