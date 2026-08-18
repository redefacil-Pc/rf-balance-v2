"""permite snapshots das estratégias configuráveis

Revision ID: a42d7e6c910f
Revises: e31a9c2f704b
"""

import sqlalchemy as sa
from alembic import op

revision = "a42d7e6c910f"
down_revision = "e31a9c2f704b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "commission_calculation_snapshots",
        "rule_set_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.alter_column(
        "commission_calculation_snapshots",
        "rule_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.add_column(
        "commission_calculation_snapshots",
        sa.Column("strategy_config_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        op.f(
            "fk_commission_calculation_snapshots_strategy_config_id_commission_strategy_configs"
        ),
        "commission_calculation_snapshots",
        "commission_strategy_configs",
        ["strategy_config_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f(
            "fk_commission_calculation_snapshots_strategy_config_id_commission_strategy_configs"
        ),
        "commission_calculation_snapshots",
        type_="foreignkey",
    )
    op.drop_column("commission_calculation_snapshots", "strategy_config_id")
    op.alter_column(
        "commission_calculation_snapshots",
        "rule_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.alter_column(
        "commission_calculation_snapshots",
        "rule_set_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
