"""Configuração versionada, snapshots e razão imutável de comissões."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class CommissionRuleSetModel(Base):
    __tablename__ = "commission_rule_sets"
    __table_args__ = (
        UniqueConstraint("strategy", "version", name="uq_commission_rule_sets_strategy_version"),
        Index(
            "ix_commission_rule_sets_strategy_status_valid_from", "strategy", "status", "valid_from"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    activated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class CommissionStrategyConfigModel(Base):
    """Versão dos parâmetros de estratégias que não são simples faixas TPS."""

    __tablename__ = "commission_strategy_configs"
    __table_args__ = (
        UniqueConstraint(
            "strategy", "version", name="uq_commission_strategy_configs_strategy_version"
        ),
        Index(
            "ix_commission_strategy_configs_strategy_status_valid_from",
            "strategy",
            "status",
            "valid_from",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    activated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class CommissionRuleModel(Base):
    __tablename__ = "commission_rules"
    __table_args__ = (
        Index("ix_commission_rules_set_regime_order", "rule_set_id", "tax_regime", "sort_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_set_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("commission_rule_sets.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    tax_regime: Mapped[str] = mapped_column(String(10), nullable=False)
    tps_min: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    tps_max: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    percentage: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CommissionRuleAssignmentModel(Base):
    __tablename__ = "commission_rule_assignments"
    __table_args__ = (
        Index("ix_commission_assignments_scope_valid_from", "scope_type", "scope_id", "valid_from"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_set_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("commission_rule_sets.id", ondelete="RESTRICT"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    tax_regime: Mapped[str | None] = mapped_column(String(10), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class CommissionBeneficiaryPolicyModel(Base):
    """Exceções individuais versionadas sem alterar regras globais."""

    __tablename__ = "commission_beneficiary_policies"
    __table_args__ = (
        Index(
            "ix_commission_beneficiary_policy_validity",
            "collaborator_id",
            "valid_from",
            "valid_to",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    collaborator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    excluded: Mapped[bool] = mapped_column(nullable=False, default=False)
    override_tps_35_percentage: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)


class CommissionCalculationSnapshotModel(Base):
    __tablename__ = "commission_calculation_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "receipt_id", "beneficiary_id", "strategy", name="uq_commission_snapshot_origin"
        ),
        Index("ix_commission_snapshots_beneficiary_date", "beneficiary_id", "competence_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_set_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("commission_rule_sets.id", ondelete="RESTRICT"), nullable=True
    )
    rule_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("commission_rules.id", ondelete="RESTRICT"), nullable=True
    )
    strategy_config_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("commission_strategy_configs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    proposal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("proposals.id", ondelete="RESTRICT"), nullable=False
    )
    receipt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False
    )
    beneficiary_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=False
    )
    strategy: Mapped[str] = mapped_column(String(40), nullable=False)
    competence_date: Mapped[date] = mapped_column(Date, nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA
    )


class CommissionEntryModel(Base):
    __tablename__ = "commission_entries"
    __table_args__ = (
        UniqueConstraint(
            "reversal_id", "snapshot_id", name="uq_commission_entries_reversal_snapshot"
        ),
        Index("ix_commission_entries_beneficiary_date", "beneficiary_id", "competence_date"),
        Index("ix_commission_entries_receipt_id", "receipt_id"),
        Index("ix_commission_entries_reversal_id", "reversal_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("commission_calculation_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    proposal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("proposals.id", ondelete="RESTRICT"), nullable=False
    )
    receipt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False
    )
    reversal_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("receipt_reversals.id", ondelete="RESTRICT"), nullable=True
    )
    beneficiary_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=False
    )
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    competence_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)


class CommissionManualEntryModel(Base):
    """Crédito manual de BKO ou bônus de Finalização."""

    __tablename__ = "commission_manual_entries"
    __table_args__ = (
        Index("ix_commission_manual_beneficiary_date", "beneficiary_id", "effective_date"),
        UniqueConstraint("created_by", "idempotency_key", name="uq_commission_manual_actor_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    beneficiary_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=False
    )
    entry_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)


class CommissionSettlementModel(Base):
    """Fechamento financeiro de uma pessoa em um período."""

    __tablename__ = "commission_settlements"
    __table_args__ = (
        UniqueConstraint(
            "beneficiary_id", "period_start", "period_end", name="uq_commission_settlement_period"
        ),
        Index("ix_commission_settlements_period_status", "period_start", "period_end", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    beneficiary_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collaborators.id", ondelete="RESTRICT"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    carryover_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    deferred_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    updated_by: Mapped[int] = mapped_column(BigInteger, nullable=False)


class CommissionPeriodModel(Base):
    """Janela operacional de apuração e seu cutoff imutável após fechamento."""

    __tablename__ = "commission_periods"
    __table_args__ = (
        UniqueConstraint("period_start", "period_end", name="uq_commission_period_range"),
        Index("ix_commission_periods_status_dates", "status", "period_start", "period_end"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    cutoff_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    closed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
