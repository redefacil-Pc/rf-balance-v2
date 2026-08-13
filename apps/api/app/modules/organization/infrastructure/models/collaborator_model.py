"""Tabela `collaborators` — pessoa operacional/financeira.

Colaborador **não** é obrigatoriamente um usuário de acesso (seção 3.2): é a
entidade que recebe comissão. O vínculo opcional com `users` existe para quem
também acessa o sistema.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA, AGORA_COM_ON_UPDATE
from app.platform.db.types.utc_datetime import UtcDateTime


class CollaboratorModel(Base):
    __tablename__ = "collaborators"
    __table_args__ = (
        # caminhos de acesso das listagens filtradas (seção 7.2)
        Index("ix_collaborators_unit_id_is_active", "unit_id", "is_active"),
        Index("ix_collaborators_company_id_is_active", "company_id", "is_active"),
        Index("ix_collaborators_full_name", "full_name"),
        # um registro do legado entra uma vez só, mesmo com o importador repetido
        UniqueConstraint("legacy_source", "legacy_id", name="uq_collaborators_legacy"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    unit_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )
    # conta de acesso, quando a pessoa também usa o sistema
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # CPF/CNPJ cifrado, com hash único para deduplicação (ADR-0012)
    document_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(4), nullable=False)
    # MEI ou CLT (seção 3.2)
    tax_regime: Mapped[str] = mapped_column(String(10), nullable=False)

    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # inativação exige data e motivo (seção 7.2)
    deactivated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    deactivation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA_COM_ON_UPDATE
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    #: rastreabilidade da migração (seção 18): de qual tabela do v1 veio e com
    #: qual id. Nulo em colaborador cadastrado direto na v2.
    legacy_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    legacy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # concorrência otimista, como em propostas
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
