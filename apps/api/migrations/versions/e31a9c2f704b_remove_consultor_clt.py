"""remove as faixas obsoletas do consultor CLT

Revision ID: e31a9c2f704b
Revises: b7e2d14c8a30
"""

import sqlalchemy as sa
from alembic import op

revision = "e31a9c2f704b"
down_revision = "b7e2d14c8a30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conexao = op.get_bind()
    conexao.execute(
        sa.text(
            "DELETE FROM commission_rules WHERE tax_regime = 'CLT' "
            "AND rule_set_id IN (SELECT id FROM commission_rule_sets "
            "WHERE strategy = 'STANDARD_CONSULTANT') "
            "AND NOT EXISTS (SELECT 1 FROM commission_calculation_snapshots snapshots "
            "WHERE snapshots.rule_id = commission_rules.id)"
        )
    )
    conexao.execute(
        sa.text(
            "UPDATE commission_rule_sets SET name = 'Consultor padrão MEI' "
            "WHERE strategy = 'STANDARD_CONSULTANT' AND name = 'Consultor padrão MEI e CLT'"
        )
    )


def downgrade() -> None:
    conexao = op.get_bind()
    conjuntos = conexao.execute(
        sa.text(
            "SELECT sets.id FROM commission_rule_sets sets "
            "WHERE sets.strategy = 'STANDARD_CONSULTANT' "
            "AND NOT EXISTS (SELECT 1 FROM commission_rules rules "
            "WHERE rules.rule_set_id = sets.id AND rules.tax_regime = 'CLT')"
        )
    ).scalars()
    regras = sa.table(
        "commission_rules",
        sa.column("rule_set_id", sa.BigInteger()),
        sa.column("role", sa.String()),
        sa.column("tax_regime", sa.String()),
        sa.column("tps_min", sa.Numeric()),
        sa.column("tps_max", sa.Numeric()),
        sa.column("percentage", sa.Numeric()),
        sa.column("sort_order", sa.BigInteger()),
        sa.column("parameters", sa.JSON()),
    )
    for conjunto_id in conjuntos:
        op.bulk_insert(
            regras,
            [
                {
                    "rule_set_id": conjunto_id,
                    "role": "CONSULTOR",
                    "tax_regime": "CLT",
                    "tps_min": minimo,
                    "tps_max": maximo,
                    "percentage": percentual,
                    "sort_order": ordem,
                    "parameters": {},
                }
                for ordem, (minimo, maximo, percentual) in enumerate(
                    ((0, 25, 6), (25, 30, 8), (30, 35, 10), (35, None, 12)), start=1
                )
            ],
        )
    conexao.execute(
        sa.text(
            "UPDATE commission_rule_sets SET name = 'Consultor padrão MEI e CLT' "
            "WHERE strategy = 'STANDARD_CONSULTANT' AND name = 'Consultor padrão MEI'"
        )
    )
