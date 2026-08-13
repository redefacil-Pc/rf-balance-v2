"""Tabela `collaborator_payment_keys` — chave PIX protegida e versionada.

PIX é dado sensível (seção 7.2): cifrado, mascarado sem permissão financeira e
**versionado** — a troca não sobrescreve, encerra a vigência da anterior. Isso
preserva a resposta a "para qual chave pagamos naquele fechamento?".
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class CollaboratorPaymentKeyModel(Base):
    __tablename__ = "collaborator_payment_keys"
    __table_args__ = (
        Index(
            "ix_collaborator_payment_keys_collaborator_id_valid_from",
            "collaborator_id",
            "valid_from",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    collaborator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="CASCADE"), nullable=False
    )
    # CPF, CNPJ, EMAIL, TELEFONE ou ALEATORIA
    key_type: Mapped[str] = mapped_column(String(12), nullable=False)
    key_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # amostra mascarada, para exibir sem decifrar e sem expor o valor
    key_masked: Mapped[str] = mapped_column(String(60), nullable=False)

    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
