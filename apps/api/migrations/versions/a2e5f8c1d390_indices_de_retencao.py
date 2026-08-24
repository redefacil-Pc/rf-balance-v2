"""índices das rotinas de retenção

Revision ID: a2e5f8c1d390
Revises: 9c1d4e7a2b60
"""

from alembic import op

revision = "a2e5f8c1d390"
down_revision = "9c1d4e7a2b60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_data_integrity_checks_checked_at",
        "data_integrity_checks",
        ["checked_at"],
    )
    op.create_index(
        "ix_stored_documents_created_at",
        "stored_documents",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_stored_documents_created_at", table_name="stored_documents")
    op.drop_index(
        "ix_data_integrity_checks_checked_at", table_name="data_integrity_checks"
    )
