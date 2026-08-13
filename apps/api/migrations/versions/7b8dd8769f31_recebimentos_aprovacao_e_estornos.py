"""recebimentos, aprovação e estornos

Revision ID: 7b8dd8769f31
Revises: 2068e9347337
"""

from alembic import op
import sqlalchemy as sa

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "7b8dd8769f31"
down_revision = "2068e9347337"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receipts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("proposal_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(30), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("proof_file_name", sa.String(255), nullable=False),
        sa.Column("proof_content_type", sa.String(100), nullable=False),
        sa.Column("proof_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("proof_storage_key", sa.String(255), nullable=False),
        sa.Column("proof_sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", UtcDateTime(), server_default=sa.text("CURRENT_TIMESTAMP(6)"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("decided_at", UtcDateTime(), nullable=True),
        sa.Column("decided_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by", "idempotency_key", name="uq_receipts_actor_idempotency"),
        sa.UniqueConstraint("proof_storage_key"),
    )
    op.create_index("ix_receipts_status_created_at", "receipts", ["status", "created_at"])
    op.create_index("ix_receipts_proposal_id_business_date", "receipts", ["proposal_id", "business_date"])
    op.create_table(
        "receipt_reversals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("receipt_id", sa.BigInteger(), nullable=False),
        sa.Column("proposal_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("created_at", UtcDateTime(), server_default=sa.text("CURRENT_TIMESTAMP(6)"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_id"),
    )
    op.create_index("ix_receipt_reversals_proposal_id_created_at", "receipt_reversals", ["proposal_id", "created_at"])


def downgrade() -> None:
    op.drop_table("receipt_reversals")
    op.drop_table("receipts")
