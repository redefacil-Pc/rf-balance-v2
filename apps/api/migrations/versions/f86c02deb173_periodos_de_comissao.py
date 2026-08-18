"""períodos de comissão

Revision ID: f86c02deb173
Revises: e75b91cda062
"""

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "f86c02deb173"
down_revision = "e75b91cda062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commission_periods",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("cutoff_at", UtcDateTime(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", UtcDateTime(), server_default=sa.text("CURRENT_TIMESTAMP(6)"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("closed_at", UtcDateTime(), nullable=True),
        sa.Column("closed_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_periods")),
        sa.UniqueConstraint("period_start", "period_end", name="uq_commission_period_range"),
    )
    op.create_index(
        "ix_commission_periods_status_dates",
        "commission_periods",
        ["status", "period_start", "period_end"],
    )


def downgrade() -> None:
    op.drop_table("commission_periods")
