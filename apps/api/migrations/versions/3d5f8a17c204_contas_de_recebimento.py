"""catálogo de contas de recebimento e vínculo com o recebimento

Revision ID: 3d5f8a17c204
Revises: 9a3c5d81b7e4
"""

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "3d5f8a17c204"
down_revision = "9a3c5d81b7e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receiving_accounts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "updated_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("label", name="uq_receiving_accounts_label"),
    )
    # o default do banco serve só para criar a coluna; o valor de negócio vem do
    # model, e deixar os dois divergindo faria o `alembic check` acusar drift
    op.alter_column("receiving_accounts", "display_order", server_default=None)
    op.alter_column("receiving_accounts", "is_active", server_default=None)
    op.add_column(
        "receipts",
        sa.Column("receiving_account_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_receipts_receiving_account",
        "receipts",
        "receiving_accounts",
        ["receiving_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_receipts_receiving_account", "receipts", type_="foreignkey")
    op.drop_column("receipts", "receiving_account_id")
    op.drop_table("receiving_accounts")
