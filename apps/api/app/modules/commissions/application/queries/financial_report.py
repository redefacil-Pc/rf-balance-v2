"""Relatório financeiro derivado de recebimentos e da razão de comissões."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commissions.domain.errors import CommissionRuleConfigurationError
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
    CommissionManualEntryModel,
    CommissionSettlementModel,
)
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.receivables.infrastructure.models.receipt_model import (
    ReceiptModel,
    ReceiptReversalModel,
)

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
CONSULTANT_STRATEGIES = frozenset({"STANDARD_CONSULTANT", "SCALED_CONSULTANT"})
LEADER_STRATEGIES = frozenset({"COMMERCIAL_LEADER", "GENERAL_MEI_LEADER"})


@dataclass(frozen=True, slots=True)
class FinancialReportSummary:
    gross_revenue: Decimal
    receipt_reversals: Decimal
    recognized_revenue: Decimal
    recognized_production: Decimal
    consultant_commissions: Decimal
    leader_commissions: Decimal
    finalization_commissions: Decimal
    finalization_leader_commissions: Decimal
    bko_commissions: Decimal
    total_commissions: Decimal
    net_billing: Decimal
    bonuses: Decimal
    discounts: Decimal
    deferred: Decimal
    paid: Decimal
    payable: Decimal


@dataclass(frozen=True, slots=True)
class FinancialReportBeneficiary:
    beneficiary_id: int
    beneficiary_name: str
    strategies: tuple[str, ...]
    automatic_amount: Decimal
    manual_amount: Decimal
    calculated_amount: Decimal
    carryover_amount: Decimal
    bonus_amount: Decimal
    discount_amount: Decimal
    deferred_amount: Decimal
    paid_amount: Decimal
    payable_amount: Decimal
    status: str | None


@dataclass(frozen=True, slots=True)
class FinancialReportDetail:
    source: str
    strategy: str
    entry_type: str
    competence_date: date
    amount: Decimal
    description: str
    proposal_id: int | None
    proposal_external_id: str | None
    customer_name: str | None
    receipt_id: int | None
    recognized_production: Decimal
    received_amount: Decimal
    received_percentage: Decimal | None
    tps_percentage: Decimal | None


@dataclass(frozen=True, slots=True)
class FinancialReportDetailSummary:
    recognized_production: Decimal
    received_amount: Decimal
    commission_amount: Decimal
    deferred_amount: Decimal


@dataclass(slots=True)
class _BeneficiaryAccumulator:
    name: str
    strategies: set[str]
    automatic: Decimal = ZERO
    manual: Decimal = ZERO


class FinancialCommissionReportQuery:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def summary(
        self, *, period_start: date, period_end: date
    ) -> tuple[FinancialReportSummary, list[FinancialReportBeneficiary]]:
        self._validate_period(period_start, period_end)
        gross_revenue = Decimal(
            await self._session.scalar(
                select(func.coalesce(func.sum(ReceiptModel.amount), 0)).where(
                    ReceiptModel.status == "APPROVED",
                    ReceiptModel.business_date >= period_start,
                    ReceiptModel.business_date <= period_end,
                )
            )
            or 0
        )
        receipt_reversals = Decimal(
            await self._session.scalar(
                select(func.coalesce(func.sum(ReceiptReversalModel.amount), 0))
                .join(ReceiptModel, ReceiptModel.id == ReceiptReversalModel.receipt_id)
                .where(
                    ReceiptModel.status == "APPROVED",
                    ReceiptReversalModel.business_date >= period_start,
                    ReceiptReversalModel.business_date <= period_end,
                )
            )
            or 0
        )
        automatic_rows = (
            await self._session.execute(
                select(
                    CommissionEntryModel.beneficiary_id,
                    CollaboratorModel.full_name,
                    CommissionCalculationSnapshotModel.strategy,
                    func.sum(CommissionEntryModel.amount),
                )
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .join(
                    CollaboratorModel,
                    CollaboratorModel.id == CommissionEntryModel.beneficiary_id,
                )
                .where(
                    CommissionEntryModel.competence_date >= period_start,
                    CommissionEntryModel.competence_date <= period_end,
                )
                .group_by(
                    CommissionEntryModel.beneficiary_id,
                    CollaboratorModel.full_name,
                    CommissionCalculationSnapshotModel.strategy,
                )
            )
        ).all()
        manual_rows = (
            await self._session.execute(
                select(
                    CommissionManualEntryModel.beneficiary_id,
                    CollaboratorModel.full_name,
                    CommissionManualEntryModel.entry_type,
                    func.sum(CommissionManualEntryModel.amount),
                )
                .join(
                    CollaboratorModel,
                    CollaboratorModel.id == CommissionManualEntryModel.beneficiary_id,
                )
                .where(
                    CommissionManualEntryModel.effective_date >= period_start,
                    CommissionManualEntryModel.effective_date <= period_end,
                )
                .group_by(
                    CommissionManualEntryModel.beneficiary_id,
                    CollaboratorModel.full_name,
                    CommissionManualEntryModel.entry_type,
                )
            )
        ).all()
        settlements = list(
            (
                await self._session.scalars(
                    select(CommissionSettlementModel).where(
                        CommissionSettlementModel.period_start == period_start,
                        CommissionSettlementModel.period_end == period_end,
                    )
                )
            ).all()
        )
        settlement_by_beneficiary = {item.beneficiary_id: item for item in settlements}
        beneficiaries: dict[int, _BeneficiaryAccumulator] = {}
        automatic_by_strategy: dict[str, Decimal] = {}
        for beneficiary_id, name, strategy, amount in automatic_rows:
            value = Decimal(amount)
            automatic_by_strategy[str(strategy)] = (
                automatic_by_strategy.get(str(strategy), ZERO) + value
            )
            item = beneficiaries.setdefault(
                int(beneficiary_id), _BeneficiaryAccumulator(str(name), set())
            )
            item.strategies.add(str(strategy))
            item.automatic += value
        manual_by_type: dict[str, Decimal] = {}
        for beneficiary_id, name, entry_type, amount in manual_rows:
            value = Decimal(amount)
            manual_by_type[str(entry_type)] = manual_by_type.get(str(entry_type), ZERO) + value
            item = beneficiaries.setdefault(
                int(beneficiary_id), _BeneficiaryAccumulator(str(name), set())
            )
            strategy = "BKO" if entry_type == "BKO_COMMISSION" else "FINALIZER"
            item.strategies.add(strategy)
            item.manual += value
        if settlement_by_beneficiary:
            names = (
                await self._session.execute(
                    select(CollaboratorModel.id, CollaboratorModel.full_name).where(
                        CollaboratorModel.id.in_(settlement_by_beneficiary)
                    )
                )
            ).all()
            for beneficiary_id, name in names:
                beneficiaries.setdefault(
                    int(beneficiary_id), _BeneficiaryAccumulator(str(name), set())
                )
        recognized_production = await self._recognized_production(period_start, period_end)
        consultant = sum(
            (automatic_by_strategy.get(item, ZERO) for item in CONSULTANT_STRATEGIES), ZERO
        )
        leaders = sum((automatic_by_strategy.get(item, ZERO) for item in LEADER_STRATEGIES), ZERO)
        finalization = automatic_by_strategy.get("FINALIZER", ZERO) + manual_by_type.get(
            "FINALIZATION_BONUS", ZERO
        )
        finalization_leader = automatic_by_strategy.get("FINALIZATION_LEADER", ZERO)
        bko = manual_by_type.get("BKO_COMMISSION", ZERO)
        total_commissions = sum(automatic_by_strategy.values(), ZERO) + sum(
            manual_by_type.values(), ZERO
        )
        recognized_revenue = gross_revenue - receipt_reversals
        report_items = [
            self._beneficiary_view(
                beneficiary_id, item, settlement_by_beneficiary.get(beneficiary_id)
            )
            for beneficiary_id, item in beneficiaries.items()
        ]
        report_items.sort(key=lambda item: item.beneficiary_name.casefold())
        return (
            FinancialReportSummary(
                gross_revenue=gross_revenue,
                receipt_reversals=receipt_reversals,
                recognized_revenue=recognized_revenue,
                recognized_production=recognized_production,
                consultant_commissions=consultant,
                leader_commissions=leaders,
                finalization_commissions=finalization,
                finalization_leader_commissions=finalization_leader,
                bko_commissions=bko,
                total_commissions=total_commissions,
                net_billing=recognized_revenue - total_commissions,
                bonuses=sum((item.bonus_amount for item in settlements), ZERO),
                discounts=sum((item.discount_amount for item in settlements), ZERO),
                deferred=sum((item.deferred_amount for item in settlements), ZERO),
                paid=sum((item.paid_amount for item in settlements), ZERO),
                payable=sum((item.payable_amount for item in settlements), ZERO),
            ),
            report_items,
        )

    async def details(
        self, *, beneficiary_id: int, period_start: date, period_end: date
    ) -> tuple[FinancialReportDetailSummary, list[FinancialReportDetail]]:
        self._validate_period(period_start, period_end)
        automatic = (
            await self._session.execute(
                select(
                    CommissionEntryModel,
                    CommissionCalculationSnapshotModel,
                    ProposalModel.external_id,
                    ProposalModel.customer_name,
                )
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .join(ProposalModel, ProposalModel.id == CommissionEntryModel.proposal_id)
                .where(
                    CommissionEntryModel.beneficiary_id == beneficiary_id,
                    CommissionEntryModel.competence_date >= period_start,
                    CommissionEntryModel.competence_date <= period_end,
                )
                .order_by(CommissionEntryModel.competence_date, CommissionEntryModel.id)
            )
        ).all()
        snapshot_ids = [snapshot.id for _, snapshot, _, _ in automatic]
        credit_by_snapshot: dict[int, Decimal] = {}
        if snapshot_ids:
            credit_rows = (
                await self._session.execute(
                    select(
                        CommissionEntryModel.snapshot_id,
                        func.sum(CommissionEntryModel.amount),
                    )
                    .where(
                        CommissionEntryModel.snapshot_id.in_(snapshot_ids),
                        CommissionEntryModel.entry_type == "CREDIT",
                    )
                    .group_by(CommissionEntryModel.snapshot_id)
                )
            ).all()
            credit_by_snapshot = {
                int(snapshot_id): Decimal(amount) for snapshot_id, amount in credit_rows
            }
        manual = list(
            (
                await self._session.scalars(
                    select(CommissionManualEntryModel)
                    .where(
                        CommissionManualEntryModel.beneficiary_id == beneficiary_id,
                        CommissionManualEntryModel.effective_date >= period_start,
                        CommissionManualEntryModel.effective_date <= period_end,
                    )
                    .order_by(
                        CommissionManualEntryModel.effective_date,
                        CommissionManualEntryModel.id,
                    )
                )
            ).all()
        )
        result: list[FinancialReportDetail] = []
        for entry, snapshot, external_id, customer_name in automatic:
            inputs = dict(snapshot.inputs)
            outputs = dict(snapshot.outputs)
            production = Decimal(
                str(outputs.get("recognized_production", inputs.get("recognized_production", "0")))
            )
            received = Decimal(str(inputs.get("receipt_eligible_amount", "0")))
            if entry.entry_type == "DEBIT":
                original_credit = credit_by_snapshot.get(snapshot.id, ZERO)
                ratio = abs(entry.amount / original_credit) if original_credit else ZERO
                production = -(production * ratio)
                received = -(received * ratio)
            production = production.quantize(CENT, rounding=ROUND_HALF_UP)
            received = received.quantize(CENT, rounding=ROUND_HALF_UP)
            company_commission = Decimal(str(inputs.get("company_commission", "0")))
            received_percentage = (
                min(abs(received) / company_commission * 100, Decimal("100"))
                if company_commission > 0
                else None
            )
            result.append(
                FinancialReportDetail(
                    source="AUTOMATIC",
                    strategy=snapshot.strategy,
                    entry_type=entry.entry_type,
                    competence_date=entry.competence_date,
                    amount=entry.amount,
                    description=entry.description,
                    proposal_id=entry.proposal_id,
                    proposal_external_id=external_id,
                    customer_name=customer_name,
                    receipt_id=entry.receipt_id,
                    recognized_production=production,
                    received_amount=received,
                    received_percentage=received_percentage,
                    tps_percentage=(
                        Decimal(str(inputs["tps"])) if inputs.get("tps") is not None else None
                    ),
                )
            )
        result.extend(
            FinancialReportDetail(
                source="MANUAL",
                strategy="BKO" if entry.entry_type == "BKO_COMMISSION" else "FINALIZER",
                entry_type=entry.entry_type,
                competence_date=entry.effective_date,
                amount=entry.amount,
                description=entry.description,
                proposal_id=None,
                proposal_external_id=None,
                customer_name=None,
                receipt_id=None,
                recognized_production=ZERO,
                received_amount=ZERO,
                received_percentage=None,
                tps_percentage=None,
            )
            for entry in manual
        )
        settlement = await self._session.scalar(
            select(CommissionSettlementModel).where(
                CommissionSettlementModel.beneficiary_id == beneficiary_id,
                CommissionSettlementModel.period_start == period_start,
                CommissionSettlementModel.period_end == period_end,
            )
        )
        ordered = sorted(
            result, key=lambda item: (item.competence_date, item.source, item.description)
        )
        return (
            FinancialReportDetailSummary(
                recognized_production=sum((item.recognized_production for item in ordered), ZERO),
                received_amount=sum((item.received_amount for item in ordered), ZERO),
                commission_amount=sum((item.amount for item in ordered), ZERO),
                deferred_amount=settlement.deferred_amount if settlement else ZERO,
            ),
            ordered,
        )

    async def _recognized_production(self, period_start: date, period_end: date) -> Decimal:
        snapshots = list(
            (
                await self._session.scalars(
                    select(CommissionCalculationSnapshotModel).where(
                        CommissionCalculationSnapshotModel.strategy.in_(CONSULTANT_STRATEGIES),
                        CommissionCalculationSnapshotModel.competence_date >= period_start,
                        CommissionCalculationSnapshotModel.competence_date <= period_end,
                    )
                )
            ).all()
        )
        return sum(
            (Decimal(str(item.outputs.get("recognized_production", "0"))) for item in snapshots),
            ZERO,
        )

    @staticmethod
    def _beneficiary_view(
        beneficiary_id: int,
        item: _BeneficiaryAccumulator,
        settlement: CommissionSettlementModel | None,
    ) -> FinancialReportBeneficiary:
        return FinancialReportBeneficiary(
            beneficiary_id=beneficiary_id,
            beneficiary_name=item.name,
            strategies=tuple(sorted(item.strategies)),
            automatic_amount=item.automatic,
            manual_amount=item.manual,
            calculated_amount=item.automatic + item.manual,
            carryover_amount=settlement.carryover_amount if settlement else ZERO,
            bonus_amount=settlement.bonus_amount if settlement else ZERO,
            discount_amount=settlement.discount_amount if settlement else ZERO,
            deferred_amount=settlement.deferred_amount if settlement else ZERO,
            paid_amount=settlement.paid_amount if settlement else ZERO,
            payable_amount=(
                settlement.payable_amount if settlement else item.automatic + item.manual
            ),
            status=settlement.status if settlement else None,
        )

    @staticmethod
    def _validate_period(period_start: date, period_end: date) -> None:
        if period_end < period_start:
            raise CommissionRuleConfigurationError("O fim do período deve ser posterior ao início.")
        if (period_end - period_start).days > 92:
            raise CommissionRuleConfigurationError("O período não pode ultrapassar 93 dias.")
