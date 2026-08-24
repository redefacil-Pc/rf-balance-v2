"""documentos financeiros em lote

Revision ID: 6f2a9c1d8b40
Revises: e4b71a09c536
"""

import sqlalchemy as sa
from alembic import op

from app.platform.db.types.utc_datetime import UtcDateTime

revision = "6f2a9c1d8b40"
down_revision = "e4b71a09c536"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("job_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("unit_id", sa.BigInteger(), nullable=True),
        sa.Column("leader_id", sa.BigInteger(), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("processed_items", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.BigInteger(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", UtcDateTime(), nullable=True),
        sa.Column("started_at", UtcDateTime(), nullable=True),
        sa.Column("completed_at", UtcDateTime(), nullable=True),
        sa.Column(
            "created_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["leader_id"], ["collaborators.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requested_by", "idempotency_key", name="uq_document_jobs_actor_key"
        ),
    )
    op.create_index(
        "ix_document_jobs_requested_by_created_at",
        "document_jobs",
        ["requested_by", "created_at"],
    )
    op.create_index(
        "ix_document_jobs_status_next_attempt",
        "document_jobs",
        ["status", "next_attempt_at"],
    )
    op.create_table(
        "stored_documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("document_key", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("beneficiary_id", sa.BigInteger(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            UtcDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["beneficiary_id"], ["collaborators.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["document_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "document_key", name="uq_stored_documents_job_key"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "ix_stored_documents_job_id_kind",
        "stored_documents",
        ["job_id", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_stored_documents_job_id_kind", table_name="stored_documents")
    op.drop_table("stored_documents")
    op.drop_index("ix_document_jobs_status_next_attempt", table_name="document_jobs")
    op.drop_index("ix_document_jobs_requested_by_created_at", table_name="document_jobs")
    op.drop_table("document_jobs")
