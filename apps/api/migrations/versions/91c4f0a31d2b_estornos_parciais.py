"""permite múltiplos estornos parciais por recebimento

Revision ID: 91c4f0a31d2b
Revises: 7b8dd8769f31
"""

from alembic import op

revision = "91c4f0a31d2b"
down_revision = "7b8dd8769f31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_receipt_reversals_receipt_id", "receipt_reversals", ["receipt_id"], unique=False
    )
    op.drop_constraint("uq_receipt_reversals_receipt_id", "receipt_reversals", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_receipt_reversals_receipt_id", "receipt_reversals", ["receipt_id"]
    )
    op.drop_index("ix_receipt_reversals_receipt_id", table_name="receipt_reversals")
