"""remove defaults temporários dos descontos de estorno

Revision ID: 9c1d4e7a2b60
Revises: 8a7c2e1f4b90
"""

import sqlalchemy as sa
from alembic import op

revision = "9c1d4e7a2b60"
down_revision = "8a7c2e1f4b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        "manual_discount_amount",
        "reversal_discount_amount",
        "reversal_carryover_amount",
    ):
        op.alter_column(
            "commission_settlements",
            column,
            existing_type=sa.Numeric(18, 2),
            existing_nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    for column in (
        "manual_discount_amount",
        "reversal_discount_amount",
        "reversal_carryover_amount",
    ):
        op.alter_column(
            "commission_settlements",
            column,
            existing_type=sa.Numeric(18, 2),
            existing_nullable=False,
            server_default=sa.text("0.00"),
        )
