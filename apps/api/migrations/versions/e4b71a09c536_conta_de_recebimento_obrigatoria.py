"""conta de recebimento obrigatória no recebimento

Nasceu opcional porque os lançamentos anteriores ao catálogo não teriam como
responder onde o dinheiro caiu. Com a base zerada, esse motivo deixou de
existir, e a coluna passa a exigir resposta: sem ela, o relatório por conta tem
uma fatia sem dono que ninguém consegue explicar depois.

Pagamento em espécie continua cabendo — cadastra-se uma conta "Caixa" no
catálogo, em vez de abrir exceção na regra.

Revision ID: e4b71a09c536
Revises: 5c92e0b41f83
"""

import sqlalchemy as sa
from alembic import op

revision = "e4b71a09c536"
down_revision = "5c92e0b41f83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "receipts",
        "receiving_account_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "receipts",
        "receiving_account_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
