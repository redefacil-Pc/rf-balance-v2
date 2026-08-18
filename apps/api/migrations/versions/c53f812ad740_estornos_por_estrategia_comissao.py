"""permite estorno de múltiplas estratégias

Revision ID: c53f812ad740
Revises: a42d7e6c910f
"""

from alembic import op

revision = "c53f812ad740"
down_revision = "a42d7e6c910f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MySQL pode reutilizar o índice UNIQUE para sustentar a FK de reversal_id;
    # dê à FK um índice próprio antes de remover a restrição antiga.
    op.create_index("ix_commission_entries_reversal_id", "commission_entries", ["reversal_id"])
    op.drop_constraint("uq_commission_entries_reversal", "commission_entries", type_="unique")
    op.create_unique_constraint(
        "uq_commission_entries_reversal_snapshot",
        "commission_entries",
        ["reversal_id", "snapshot_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_commission_entries_reversal_snapshot", "commission_entries", type_="unique"
    )
    op.create_unique_constraint(
        "uq_commission_entries_reversal",
        "commission_entries",
        ["reversal_id", "beneficiary_id"],
    )
    op.drop_index("ix_commission_entries_reversal_id", table_name="commission_entries")
