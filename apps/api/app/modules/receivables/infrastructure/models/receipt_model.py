from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class ReceiptModel(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("created_by", "idempotency_key", name="uq_receipts_actor_idempotency"),
        Index("ix_receipts_status_created_at", "status", "created_at"),
        Index("ix_receipts_proposal_id_business_date", "proposal_id", "business_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("proposals.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_datetime: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    # em qual conta da casa o dinheiro caiu. Opcional porque os recebimentos
    # lançados antes do catálogo existir não têm como responder isso
    receiving_account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("receiving_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="SUBMITTED")
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    proof_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    proof_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    proof_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    proof_storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    proof_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class ReceiptReversalModel(Base):
    __tablename__ = "receipt_reversals"
    __table_args__ = (
        Index("ix_receipt_reversals_receipt_id", "receipt_id"),
        Index("ix_receipt_reversals_proposal_id_created_at", "proposal_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False
    )
    proposal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("proposals.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
