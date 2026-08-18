"""Visão consolidada e escopada do dashboard operacional."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.application.ports.proposal_scope import EscopoDePropostas
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    condicao_de_escopo,
)
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionEntryModel,
    CommissionManualEntryModel,
)
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.receivables.infrastructure.models.receipt_model import (
    ReceiptModel,
    ReceiptReversalModel,
)

ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    proposal_count: int
    open_count: int
    partially_paid_count: int
    paid_count: int
    cancelled_count: int
    pending_approval_count: int
    approved_production: Decimal
    company_commission: Decimal
    recognized_revenue: Decimal
    total_commissions: Decimal
    net_revenue: Decimal
    outstanding_amount: Decimal
    average_tps: Decimal


@dataclass(frozen=True, slots=True)
class DashboardTrend:
    business_date: date
    proposal_count: int
    production_amount: Decimal
    recognized_revenue: Decimal


@dataclass(frozen=True, slots=True)
class DashboardRanking:
    collaborator_id: int
    collaborator_name: str
    proposal_count: int
    production_amount: Decimal


@dataclass(frozen=True, slots=True)
class DashboardView:
    period_start: date
    period_end: date
    summary: DashboardSummary
    trend: list[DashboardTrend]
    ranking: list[DashboardRanking]


class DashboardQuery:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        period_start: date,
        period_end: date,
        scope: EscopoDePropostas,
    ) -> DashboardView:
        if period_end < period_start:
            raise ValueError("a data final deve ser igual ou posterior à data inicial")

        proposal_filter = [
            ProposalModel.business_date >= period_start,
            ProposalModel.business_date <= period_end,
        ]
        if not scope.irrestrito:
            proposal_filter.append(condicao_de_escopo(scope))

        approved = (ProposalModel.approval_status == "APPROVED") & (
            ProposalModel.status != "CANCELLED"
        )
        row = (
            await self._session.execute(
                select(
                    func.count(ProposalModel.id),
                    func.coalesce(func.sum(case((ProposalModel.status == "OPEN", 1), else_=0)), 0),
                    func.coalesce(
                        func.sum(case((ProposalModel.status == "PARTIALLY_PAID", 1), else_=0)), 0
                    ),
                    func.coalesce(func.sum(case((ProposalModel.status == "PAID", 1), else_=0)), 0),
                    func.coalesce(
                        func.sum(case((ProposalModel.status == "CANCELLED", 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((ProposalModel.approval_status == "SUBMITTED", 1), else_=0)),
                        0,
                    ),
                    func.coalesce(
                        func.sum(case((approved, ProposalModel.operation_amount), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(
                            case((approved, ProposalModel.company_commission_amount), else_=0)
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case((approved, ProposalModel.outstanding_amount_cached), else_=0)
                        ),
                        0,
                    ),
                    func.coalesce(func.avg(case((approved, ProposalModel.tps_percentage))), 0),
                ).where(*proposal_filter)
            )
        ).one()

        recognized_revenue = await self._recognized_revenue(
            period_start=period_start, period_end=period_end, scope=scope
        )
        total_commissions = await self._commissions(
            period_start=period_start, period_end=period_end, scope=scope
        )
        summary = DashboardSummary(
            proposal_count=int(row[0]),
            open_count=int(row[1]),
            partially_paid_count=int(row[2]),
            paid_count=int(row[3]),
            cancelled_count=int(row[4]),
            pending_approval_count=int(row[5]),
            approved_production=Decimal(row[6]),
            company_commission=Decimal(row[7]),
            recognized_revenue=recognized_revenue,
            total_commissions=total_commissions,
            net_revenue=recognized_revenue - total_commissions,
            outstanding_amount=Decimal(row[8]),
            average_tps=Decimal(row[9]),
        )
        return DashboardView(
            period_start=period_start,
            period_end=period_end,
            summary=summary,
            trend=await self._trend(period_start, period_end, scope),
            ranking=await self._ranking(period_start, period_end, scope),
        )

    async def _recognized_revenue(
        self, period_start: date, period_end: date, scope: EscopoDePropostas
    ) -> Decimal:
        receipt_query = (
            select(func.coalesce(func.sum(ReceiptModel.amount), 0))
            .join(ProposalModel, ProposalModel.id == ReceiptModel.proposal_id)
            .where(
                ReceiptModel.status == "APPROVED",
                ReceiptModel.business_date >= period_start,
                ReceiptModel.business_date <= period_end,
            )
        )
        reversal_query = (
            select(func.coalesce(func.sum(ReceiptReversalModel.amount), 0))
            .join(ReceiptModel, ReceiptModel.id == ReceiptReversalModel.receipt_id)
            .join(ProposalModel, ProposalModel.id == ReceiptReversalModel.proposal_id)
            .where(
                ReceiptModel.status == "APPROVED",
                ReceiptReversalModel.business_date >= period_start,
                ReceiptReversalModel.business_date <= period_end,
            )
        )
        if not scope.irrestrito:
            condition = condicao_de_escopo(scope)
            receipt_query = receipt_query.where(condition)
            reversal_query = reversal_query.where(condition)
        receipts = Decimal(await self._session.scalar(receipt_query) or 0)
        reversals = Decimal(await self._session.scalar(reversal_query) or 0)
        return receipts - reversals

    async def _commissions(
        self, period_start: date, period_end: date, scope: EscopoDePropostas
    ) -> Decimal:
        if not scope.irrestrito and not scope.colaboradores:
            return ZERO
        automatic = select(func.coalesce(func.sum(CommissionEntryModel.amount), 0)).where(
            CommissionEntryModel.competence_date >= period_start,
            CommissionEntryModel.competence_date <= period_end,
        )
        manual = select(func.coalesce(func.sum(CommissionManualEntryModel.amount), 0)).where(
            CommissionManualEntryModel.effective_date >= period_start,
            CommissionManualEntryModel.effective_date <= period_end,
        )
        if not scope.irrestrito:
            automatic = automatic.where(
                CommissionEntryModel.beneficiary_id.in_(scope.colaboradores)
            )
            manual = manual.where(
                CommissionManualEntryModel.beneficiary_id.in_(scope.colaboradores)
            )
        return Decimal(await self._session.scalar(automatic) or 0) + Decimal(
            await self._session.scalar(manual) or 0
        )

    async def _trend(
        self, period_start: date, period_end: date, scope: EscopoDePropostas
    ) -> list[DashboardTrend]:
        filters = [
            ProposalModel.business_date >= period_start,
            ProposalModel.business_date <= period_end,
            ProposalModel.approval_status == "APPROVED",
            ProposalModel.status != "CANCELLED",
        ]
        if not scope.irrestrito:
            filters.append(condicao_de_escopo(scope))
        proposal_rows = (
            await self._session.execute(
                select(
                    ProposalModel.business_date,
                    func.count(ProposalModel.id),
                    func.sum(ProposalModel.operation_amount),
                )
                .where(*filters)
                .group_by(ProposalModel.business_date)
                .order_by(ProposalModel.business_date)
            )
        ).all()

        receipt_query = (
            select(ReceiptModel.business_date, func.sum(ReceiptModel.amount))
            .join(ProposalModel, ProposalModel.id == ReceiptModel.proposal_id)
            .where(
                ReceiptModel.status == "APPROVED",
                ReceiptModel.business_date >= period_start,
                ReceiptModel.business_date <= period_end,
            )
        )
        if not scope.irrestrito:
            receipt_query = receipt_query.where(condicao_de_escopo(scope))
        receipt_rows = (
            await self._session.execute(
                receipt_query.group_by(ReceiptModel.business_date).order_by(
                    ReceiptModel.business_date
                )
            )
        ).all()
        reversal_query = (
            select(ReceiptReversalModel.business_date, func.sum(ReceiptReversalModel.amount))
            .join(ReceiptModel, ReceiptModel.id == ReceiptReversalModel.receipt_id)
            .join(ProposalModel, ProposalModel.id == ReceiptReversalModel.proposal_id)
            .where(
                ReceiptModel.status == "APPROVED",
                ReceiptReversalModel.business_date >= period_start,
                ReceiptReversalModel.business_date <= period_end,
            )
        )
        if not scope.irrestrito:
            reversal_query = reversal_query.where(condicao_de_escopo(scope))
        reversal_rows = (
            await self._session.execute(
                reversal_query.group_by(ReceiptReversalModel.business_date).order_by(
                    ReceiptReversalModel.business_date
                )
            )
        ).all()
        by_date: dict[date, DashboardTrend] = {
            row_date: DashboardTrend(row_date, int(count), Decimal(production), ZERO)
            for row_date, count, production in proposal_rows
        }
        for row_date, revenue in receipt_rows:
            current = by_date.get(row_date, DashboardTrend(row_date, 0, ZERO, ZERO))
            by_date[row_date] = DashboardTrend(
                row_date,
                current.proposal_count,
                current.production_amount,
                Decimal(revenue),
            )
        for row_date, reversal in reversal_rows:
            current = by_date.get(row_date, DashboardTrend(row_date, 0, ZERO, ZERO))
            by_date[row_date] = DashboardTrend(
                row_date,
                current.proposal_count,
                current.production_amount,
                current.recognized_revenue - Decimal(reversal),
            )
        return [by_date[item] for item in sorted(by_date)]

    async def _ranking(
        self, period_start: date, period_end: date, scope: EscopoDePropostas
    ) -> list[DashboardRanking]:
        filters = [
            ProposalModel.business_date >= period_start,
            ProposalModel.business_date <= period_end,
            ProposalModel.approval_status == "APPROVED",
            ProposalModel.status != "CANCELLED",
        ]
        if not scope.irrestrito:
            filters.append(condicao_de_escopo(scope))
        rows = (
            await self._session.execute(
                select(
                    ProposalModel.consultant_id,
                    CollaboratorModel.full_name,
                    func.count(ProposalModel.id),
                    func.sum(ProposalModel.operation_amount).label("production"),
                )
                .join(CollaboratorModel, CollaboratorModel.id == ProposalModel.consultant_id)
                .where(*filters)
                .group_by(ProposalModel.consultant_id, CollaboratorModel.full_name)
                .order_by(func.sum(ProposalModel.operation_amount).desc())
                .limit(5)
            )
        ).all()
        return [
            DashboardRanking(int(item_id), str(name), int(count), Decimal(production))
            for item_id, name, count, production in rows
        ]
