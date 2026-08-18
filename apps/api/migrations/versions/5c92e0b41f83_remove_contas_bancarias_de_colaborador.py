"""remove contas bancárias de colaborador

O pagamento de comissão sai pela chave PIX cadastrada no colaborador, e não por
agência e conta. A tabela existia por herança do desenho original e nunca teve
uso: mantê-la significaria pedir dado bancário que ninguém consulta, com PII
cifrada para proteger.

Não confundir com `receiving_accounts`, criada em 3d5f8a17c204: aquela é o outro
lado do fluxo — em qual conta da casa o cliente depositou.

Revision ID: 5c92e0b41f83
Revises: 3d5f8a17c204
"""

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "5c92e0b41f83"
down_revision = "3d5f8a17c204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("bank_accounts")


def downgrade() -> None:
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("owner_type", sa.String(12), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=True),
        sa.Column("bank_code", sa.String(5), nullable=False),
        sa.Column("bank_name", sa.String(120), nullable=False),
        sa.Column("branch", sa.String(10), nullable=False),
        sa.Column("account_encrypted", sa.String(255), nullable=False),
        sa.Column("account_masked", sa.String(30), nullable=False),
        sa.Column("account_type", sa.String(12), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bank_accounts_owner", "bank_accounts", ["owner_type", "owner_id"])
