"""adiciona horário efetivo do recebimento

Revision ID: d26be47ac912
Revises: c81d94f23a11
"""

from alembic import op
import sqlalchemy as sa

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "d26be47ac912"
down_revision = "c81d94f23a11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("receipts", sa.Column("payment_datetime", UtcDateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("receipts", "payment_datetime")
