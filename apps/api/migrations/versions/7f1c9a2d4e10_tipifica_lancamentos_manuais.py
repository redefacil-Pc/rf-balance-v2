"""tipifica lançamentos manuais de comissão

Revision ID: 7f1c9a2d4e10
Revises: 0b3e7c9a214d
"""

import sqlalchemy as sa
from alembic import op

revision = "7f1c9a2d4e10"
down_revision = "0b3e7c9a214d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "commission_manual_entries",
        sa.Column(
            "entry_type",
            sa.String(30),
            nullable=False,
            server_default="BKO_COMMISSION",
        ),
    )
    op.alter_column("commission_manual_entries", "entry_type", server_default=None)


def downgrade() -> None:
    op.drop_column("commission_manual_entries", "entry_type")
