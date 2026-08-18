"""fechamentos e BKO manual

Revision ID: d64a0f2be851
Revises: c53f812ad740
"""

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "d64a0f2be851"
down_revision = "c53f812ad740"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commission_manual_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("beneficiary_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("created_at", UtcDateTime(), server_default=sa.text("CURRENT_TIMESTAMP(6)"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["collaborators.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_manual_entries")),
        sa.UniqueConstraint("created_by", "idempotency_key", name="uq_commission_manual_actor_key"),
    )
    op.create_index(
        "ix_commission_manual_beneficiary_date",
        "commission_manual_entries",
        ["beneficiary_id", "effective_date"],
    )
    op.create_table(
        "commission_settlements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("beneficiary_id", sa.BigInteger(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("carryover_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("bonus_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("deferred_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payable_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("payment_method", sa.String(30), nullable=True),
        sa.Column("payment_reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", UtcDateTime(), server_default=sa.text("CURRENT_TIMESTAMP(6)"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", UtcDateTime(), server_default=sa.text("CURRENT_TIMESTAMP(6)"), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["collaborators.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_settlements")),
        sa.UniqueConstraint(
            "beneficiary_id", "period_start", "period_end", name="uq_commission_settlement_period"
        ),
    )
    op.create_index(
        "ix_commission_settlements_period_status",
        "commission_settlements",
        ["period_start", "period_end", "status"],
    )


def downgrade() -> None:
    op.drop_table("commission_settlements")
    op.drop_table("commission_manual_entries")
