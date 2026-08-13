"""Tabela `proposals` — campos canônicos da seção 7.4.

Aggregate comercial único: nada de `sales` ou `propostas` paralelas. Os valores
`paid_amount_cached` e `outstanding_amount_cached` são **cache** consolidado pelo
módulo de recebíveis no mesmo commit do recebimento; a verdade dos pagamentos
está em `receipts`, e a divergência entre os dois é verificada por rotina em
`data_integrity_checks`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA, AGORA_COM_ON_UPDATE
from app.platform.db.types.utc_datetime import UtcDateTime


class ProposalModel(Base):
    __tablename__ = "proposals"
    __table_args__ = (
        # invariantes da seção 7.4 no banco, não só em Python
        # `name` é o sufixo: a convenção de metadata.py prefixa com `ck_proposals_`
        CheckConstraint("operation_amount > 0", name="operation_amount_positivo"),
        CheckConstraint("tps_percentage >= 0 AND tps_percentage <= 100", name="tps_percentage"),
        # listagem padrão: situação + data de negócio
        Index("ix_proposals_status_business_date", "status", "business_date"),
        # "as propostas deste consultor no período" — base do relatório individual
        Index("ix_proposals_consultant_id_business_date", "consultant_id", "business_date"),
        # busca por cliente sem decifrar linha a linha (ADR-0012)
        Index("ix_proposals_customer_document_hash", "customer_document_hash"),
        # fila do financeiro: "o que está aguardando decisão, do mais antigo"
        Index("ix_proposals_approval_status_submitted_at", "approval_status", "submitted_at"),
        # um registro do legado entra uma vez só, mesmo com o importador repetido
        UniqueConstraint("legacy_source", "legacy_id", name="uq_proposals_legacy"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #: Redmine/ID do legado — único quando preenchido, nulo quando não há
    external_id: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True)

    consultant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=False
    )
    bko_collaborator_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=True
    )
    finalizer_collaborator_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=True
    )

    #: data operacional (America/Sao_Paulo), distinta de `created_at` em UTC
    business_date: Mapped[date] = mapped_column(Date, nullable=False)

    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_document_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    #: hash determinístico para busca; o mesmo cliente pode ter várias propostas
    customer_document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_document_type: Mapped[str] = mapped_column(String(4), nullable=False)

    operation_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tps_percentage: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    company_commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount_cached: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    outstanding_amount_cached: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    #: OPEN, PARTIALLY_PAID, PAID ou CANCELLED — VARCHAR, não ENUM do MySQL
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    #: fluxo cadastro → financeiro: DRAFT, SUBMITTED, APPROVED ou REJECTED.
    #: Dimensão separada do status financeiro — rejeitada-e-paga não existe.
    approval_status: Mapped[str] = mapped_column(String(12), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    submitted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    #: decisão mais recente do financeiro (aprovação ou devolução)
    decided_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: qual política de tolerância decidiu a quitação (seção 7.4)
    tolerance_policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    #: preenchido pelo motor de comissão na F4; sem FK enquanto a tabela não existe
    commission_snapshot_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA_COM_ON_UPDATE
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    #: motivo obrigatório no cancelamento, como em toda baixa de dado financeiro
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: rastreabilidade da migração (seção 18): de qual tabela do v1 veio e com
    #: qual id. Nulo em proposta nascida na v2.
    legacy_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    legacy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    #: controle otimista — evita sobrescrita concorrente (seção 7.4)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
