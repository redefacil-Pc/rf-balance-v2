"""registra verificações periódicas de integridade

Revision ID: c81d94f23a11
Revises: 91c4f0a31d2b
"""

from alembic import op
import sqlalchemy as sa

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "c81d94f23a11"
down_revision = "91c4f0a31d2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_integrity_checks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("check_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "checked_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_integrity_checks_check_type",
        "data_integrity_checks",
        ["check_type"],
    )


def downgrade() -> None:
    op.drop_table("data_integrity_checks")
