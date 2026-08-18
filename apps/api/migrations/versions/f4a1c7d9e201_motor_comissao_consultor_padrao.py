"""motor de comissão do consultor padrão

Revision ID: f4a1c7d9e201
Revises: d26be47ac912
"""

from datetime import date

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "f4a1c7d9e201"
down_revision = "d26be47ac912"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commission_rule_sets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("strategy", sa.String(40), nullable=False),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "activated_at",
            UtcDateTime(),
            nullable=True,
        ),
        sa.Column("activated_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_rule_sets")),
        sa.UniqueConstraint("strategy", "version", name="uq_commission_rule_sets_strategy_version"),
    )
    op.create_index(
        "ix_commission_rule_sets_strategy_status_valid_from",
        "commission_rule_sets",
        ["strategy", "status", "valid_from"],
    )
    op.create_table(
        "commission_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rule_set_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("tax_regime", sa.String(10), nullable=False),
        sa.Column("tps_min", sa.Numeric(9, 6), nullable=False),
        sa.Column("tps_max", sa.Numeric(9, 6), nullable=True),
        sa.Column("percentage", sa.Numeric(9, 6), nullable=False),
        sa.Column("sort_order", sa.BigInteger(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["commission_rule_sets.id"],
            name=op.f("fk_commission_rules_rule_set_id_commission_rule_sets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_rules")),
    )
    op.create_index(
        "ix_commission_rules_set_regime_order",
        "commission_rules",
        ["rule_set_id", "tax_regime", "sort_order"],
    )
    op.create_table(
        "commission_rule_assignments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rule_set_id", sa.BigInteger(), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.BigInteger(), nullable=True),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("tax_regime", sa.String(10), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["commission_rule_sets.id"],
            name=op.f("fk_commission_rule_assignments_rule_set_id_commission_rule_sets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_rule_assignments")),
    )
    op.create_index(
        "ix_commission_assignments_scope_valid_from",
        "commission_rule_assignments",
        ["scope_type", "scope_id", "valid_from"],
    )
    op.create_table(
        "commission_calculation_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rule_set_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("proposal_id", sa.BigInteger(), nullable=False),
        sa.Column("receipt_id", sa.BigInteger(), nullable=False),
        sa.Column("beneficiary_id", sa.BigInteger(), nullable=False),
        sa.Column("strategy", sa.String(40), nullable=False),
        sa.Column("competence_date", sa.Date(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("outputs", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column(
            "calculated_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["beneficiary_id"],
            ["collaborators.id"],
            name=op.f("fk_commission_calculation_snapshots_beneficiary_id_collaborators"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["proposals.id"],
            name=op.f("fk_commission_calculation_snapshots_proposal_id_proposals"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name=op.f("fk_commission_calculation_snapshots_receipt_id_receipts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["commission_rules.id"],
            name=op.f("fk_commission_calculation_snapshots_rule_id_commission_rules"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["commission_rule_sets.id"],
            name=op.f("fk_commission_calculation_snapshots_rule_set_id_commission_rule_sets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_calculation_snapshots")),
        sa.UniqueConstraint(
            "receipt_id", "beneficiary_id", "strategy", name="uq_commission_snapshot_origin"
        ),
    )
    op.create_index(
        "ix_commission_snapshots_beneficiary_date",
        "commission_calculation_snapshots",
        ["beneficiary_id", "competence_date"],
    )
    op.create_table(
        "commission_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.BigInteger(), nullable=False),
        sa.Column("proposal_id", sa.BigInteger(), nullable=False),
        sa.Column("receipt_id", sa.BigInteger(), nullable=False),
        sa.Column("reversal_id", sa.BigInteger(), nullable=True),
        sa.Column("beneficiary_id", sa.BigInteger(), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("competence_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["beneficiary_id"],
            ["collaborators.id"],
            name=op.f("fk_commission_entries_beneficiary_id_collaborators"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["proposals.id"],
            name=op.f("fk_commission_entries_proposal_id_proposals"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name=op.f("fk_commission_entries_receipt_id_receipts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reversal_id"],
            ["receipt_reversals.id"],
            name=op.f("fk_commission_entries_reversal_id_receipt_reversals"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["commission_calculation_snapshots.id"],
            name=op.f("fk_commission_entries_snapshot_id_commission_calculation_snapshots"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_entries")),
        sa.UniqueConstraint("reversal_id", "beneficiary_id", name="uq_commission_entries_reversal"),
    )
    op.create_index(
        "ix_commission_entries_beneficiary_date",
        "commission_entries",
        ["beneficiary_id", "competence_date"],
    )
    op.create_index("ix_commission_entries_receipt_id", "commission_entries", ["receipt_id"])

    conjuntos = sa.table(
        "commission_rule_sets",
        sa.column("id", sa.BigInteger()),
        sa.column("strategy", sa.String()),
        sa.column("version", sa.String()),
        sa.column("name", sa.String()),
        sa.column("status", sa.String()),
        sa.column("valid_from", sa.Date()),
        sa.column("valid_to", sa.Date()),
        sa.column("reason", sa.Text()),
    )
    op.bulk_insert(
        conjuntos,
        [
            {
                "id": 1,
                "strategy": "STANDARD_CONSULTANT",
                "version": "2026.1",
                "name": "Consultor padrão MEI e CLT",
                "status": "ACTIVE",
                "valid_from": date(2000, 1, 1),
                "valid_to": None,
                "reason": "Defaults levantados e validados em 14/08/2026",
            }
        ],
    )
    regras = sa.table(
        "commission_rules",
        sa.column("id", sa.BigInteger()),
        sa.column("rule_set_id", sa.BigInteger()),
        sa.column("role", sa.String()),
        sa.column("tax_regime", sa.String()),
        sa.column("tps_min", sa.Numeric()),
        sa.column("tps_max", sa.Numeric()),
        sa.column("percentage", sa.Numeric()),
        sa.column("sort_order", sa.BigInteger()),
        sa.column("parameters", sa.JSON()),
    )
    linhas = []
    identificador = 1
    for regime in ("MEI", "CLT"):
        for ordem, (minimo, maximo, percentual) in enumerate(
            ((0, 25, 6), (25, 30, 8), (30, 35, 10), (35, None, 12)), 1
        ):
            linhas.append(
                {
                    "id": identificador,
                    "rule_set_id": 1,
                    "role": "CONSULTOR",
                    "tax_regime": regime,
                    "tps_min": minimo,
                    "tps_max": maximo,
                    "percentage": percentual,
                    "sort_order": ordem,
                    "parameters": {},
                }
            )
            identificador += 1
    op.bulk_insert(regras, linhas)


def downgrade() -> None:
    op.drop_table("commission_entries")
    op.drop_table("commission_calculation_snapshots")
    op.drop_table("commission_rule_assignments")
    op.drop_table("commission_rules")
    op.drop_table("commission_rule_sets")
