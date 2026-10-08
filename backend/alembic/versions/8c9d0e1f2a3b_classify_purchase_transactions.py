"""Classify historical manual grants separately from paid transactions."""

from alembic import op
import sqlalchemy as sa

revision = "8c9d0e1f2a3b"
down_revision = "7b8c9d0e1f2a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "purchases",
        sa.Column(
            "transaction_kind", sa.String(20), nullable=False, server_default="paid"
        ),
    )
    op.execute(
        "UPDATE purchases SET transaction_kind = 'manual_grant' WHERE left(payment_id, 12) = 'admin_grant_'"
    )
    op.create_check_constraint(
        "ck_purchase_transaction_kind",
        "purchases",
        "transaction_kind IN ('paid', 'manual_grant')",
    )


def downgrade():
    op.drop_constraint("ck_purchase_transaction_kind", "purchases", type_="check")
    op.drop_column("purchases", "transaction_kind")
