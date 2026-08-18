"""reabertura de período de comissão

Revision ID: 9a3c5d81b7e4
Revises: 7f1c9a2d4e10
"""

import sqlalchemy as sa
from alembic import op

revision = "9a3c5d81b7e4"
down_revision = "7f1c9a2d4e10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "commission_periods",
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "commission_periods",
        sa.Column("reopened_by", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "commission_periods",
        sa.Column("reopen_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("commission_periods", "reopen_reason")
    op.drop_column("commission_periods", "reopened_by")
    op.drop_column("commission_periods", "reopened_at")
