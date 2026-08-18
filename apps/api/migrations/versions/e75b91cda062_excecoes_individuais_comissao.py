"""exceções individuais de comissão

Revision ID: e75b91cda062
Revises: d64a0f2be851
"""

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "e75b91cda062"
down_revision = "d64a0f2be851"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commission_beneficiary_policies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("collaborator_id", sa.BigInteger(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("excluded", sa.Boolean(), nullable=False),
        sa.Column("override_tps_35_percentage", sa.Numeric(9, 6), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["collaborator_id"], ["collaborators.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_beneficiary_policies")),
    )
    op.create_index(
        "ix_commission_beneficiary_policy_validity",
        "commission_beneficiary_policies",
        ["collaborator_id", "valid_from", "valid_to"],
    )


def downgrade() -> None:
    op.drop_table("commission_beneficiary_policies")
