"""Tabela `bank_accounts` — contas de destino de pagamento."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA, AGORA_COM_ON_UPDATE
from app.platform.db.types.utc_datetime import UtcDateTime


class BankAccountModel(Base):
    __tablename__ = "bank_accounts"
    __table_args__ = (Index("ix_bank_accounts_owner", "owner_type", "owner_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # COMPANY, UNIT ou COLLABORATOR — a conta pertence a um dos três
    owner_type: Mapped[str] = mapped_column(String(12), nullable=False)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    company_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True
    )

    bank_code: Mapped[str] = mapped_column(String(5), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    branch: Mapped[str] = mapped_column(String(10), nullable=False)
    # número da conta cifrado; a exibição usa os últimos dígitos
    account_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    account_masked: Mapped[str] = mapped_column(String(30), nullable=False)
    account_type: Mapped[str] = mapped_column(String(12), nullable=False, default="CORRENTE")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA_COM_ON_UPDATE
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
