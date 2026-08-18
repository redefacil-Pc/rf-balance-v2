"""configurações das demais estratégias de comissão

Revision ID: b7e2d14c8a30
Revises: f4a1c7d9e201
"""

from datetime import date

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "b7e2d14c8a30"
down_revision = "f4a1c7d9e201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commission_strategy_configs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("strategy", sa.String(40), nullable=False),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("activated_at", UtcDateTime(), nullable=True),
        sa.Column("activated_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_strategy_configs")),
        sa.UniqueConstraint(
            "strategy", "version", name="uq_commission_strategy_configs_strategy_version"
        ),
    )
    op.create_index(
        "ix_commission_strategy_configs_strategy_status_valid_from",
        "commission_strategy_configs",
        ["strategy", "status", "valid_from"],
    )
    tabela = sa.table(
        "commission_strategy_configs",
        sa.column("id", sa.BigInteger()),
        sa.column("strategy", sa.String()),
        sa.column("version", sa.String()),
        sa.column("name", sa.String()),
        sa.column("status", sa.String()),
        sa.column("valid_from", sa.Date()),
        sa.column("valid_to", sa.Date()),
        sa.column("config", sa.JSON()),
        sa.column("reason", sa.Text()),
    )
    op.bulk_insert(
        tabela,
        [
            {
                "id": 1,
                "strategy": "SCALED_CONSULTANT",
                "version": "2026.1",
                "name": "Consultor MEI Escalonado",
                "status": "ACTIVE",
                "valid_from": date(2000, 1, 1),
                "valid_to": None,
                "reason": "Defaults levantados em 14/08/2026",
                "config": {
                    "display_mode": "WEEKLY",
                    "production_ranges": [
                        {"min": "0", "max": "75000", "percentages": ["8", "6", "4", "2"]},
                        {"min": "75000", "max": "175000", "percentages": ["10", "8", "6", "4"]},
                        {
                            "min": "175000",
                            "max": None,
                            "percentages": ["11.5", "9.5", "7.5", "5.5"],
                        },
                    ],
                    "tps_ranges": [
                        {"min": "35", "max": None},
                        {"min": "30", "max": "35"},
                        {"min": "25", "max": "30"},
                        {"min": "0", "max": "25"},
                    ],
                },
            },
            {
                "id": 2,
                "strategy": "COMMERCIAL_LEADER",
                "version": "2026.1",
                "name": "Líder comercial",
                "status": "ACTIVE",
                "valid_from": date(2000, 1, 1),
                "valid_to": None,
                "reason": "Defaults levantados em 14/08/2026",
                "config": {"mei_min_tps": "25", "mei_percentage": "3", "clt_percentage": "0"},
            },
            {
                "id": 3,
                "strategy": "GENERAL_MEI_LEADER",
                "version": "2026.1",
                "name": "Líder MEI geral",
                "status": "ACTIVE",
                "valid_from": date(2000, 1, 1),
                "valid_to": None,
                "reason": "Defaults levantados em 14/08/2026",
                "config": {
                    "base_percentage": "35",
                    "tiers": [
                        {"min": "0", "max": "500000", "percentage": "1.2"},
                        {"min": "500000", "max": "1000000", "percentage": "1"},
                        {"min": "1000000", "max": "1600000", "percentage": "0.8"},
                        {"min": "1600000", "max": "2400000", "percentage": "0.6"},
                        {"min": "2400000", "max": "3400000", "percentage": "0.4"},
                        {"min": "3400000", "max": "4400000", "percentage": "0.3"},
                        {"min": "4400000", "max": "5400000", "percentage": "0.2"},
                    ],
                },
            },
            {
                "id": 4,
                "strategy": "FINALIZER",
                "version": "2026.1",
                "name": "Finalização",
                "status": "ACTIVE",
                "valid_from": date(2000, 1, 1),
                "valid_to": None,
                "reason": "Defaults levantados em 14/08/2026",
                "config": {
                    "threshold_amount": "70000",
                    "fixed_amount": "500",
                    "excess_percentage": "0.45",
                },
            },
            {
                "id": 5,
                "strategy": "FINALIZATION_LEADER",
                "version": "2026.1",
                "name": "Líder de Finalização",
                "status": "ACTIVE",
                "valid_from": date(2000, 1, 1),
                "valid_to": None,
                "reason": "Defaults levantados em 14/08/2026",
                "config": {"mei_percentage": "0.9", "clt_percentage": "0.9"},
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("commission_strategy_configs")
