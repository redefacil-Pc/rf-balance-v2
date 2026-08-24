"""dupla aprovação de reabertura e desconto de estorno

Revision ID: 8a7c2e1f4b90
Revises: 6f2a9c1d8b40
"""

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "8a7c2e1f4b90"
down_revision = "6f2a9c1d8b40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "commission_settlements",
        sa.Column(
            "manual_discount_amount",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    op.add_column(
        "commission_settlements",
        sa.Column(
            "reversal_discount_amount",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    op.add_column(
        "commission_settlements",
        sa.Column(
            "reversal_carryover_amount",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    op.execute(
        "UPDATE commission_settlements "
        "SET manual_discount_amount = discount_amount"
    )
    op.alter_column(
        "commission_periods",
        "status",
        existing_type=sa.String(length=12),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.add_column(
        "commission_periods",
        sa.Column("reopen_requested_at", UtcDateTime(), nullable=True),
    )
    op.add_column(
        "commission_periods",
        sa.Column("reopen_requested_by", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("commission_periods", "reopen_requested_by")
    op.drop_column("commission_periods", "reopen_requested_at")
    op.alter_column(
        "commission_periods",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=12),
        existing_nullable=False,
    )
    op.drop_column("commission_settlements", "reversal_carryover_amount")
    op.drop_column("commission_settlements", "reversal_discount_amount")
    op.drop_column("commission_settlements", "manual_discount_amount")
