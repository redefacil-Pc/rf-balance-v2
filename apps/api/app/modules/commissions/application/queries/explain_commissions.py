"""Consulta somente-leitura da memória de cálculo e da razão de comissões."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
    CommissionRuleSetModel,
    CommissionStrategyConfigModel,
)
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel


@dataclass(frozen=True, slots=True)
class ExplainedEntry:
    id: int
    entry_type: str
    amount: Decimal
    competence_date: date
    description: str
    reversal_id: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ExplainedCalculation:
    id: int
    proposal_id: int
    receipt_id: int
    beneficiary_id: int
    beneficiary_name: str
    strategy: str
    rule_version: str | None
    competence_date: date
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    calculated_at: datetime
    entries: tuple[ExplainedEntry, ...]
    net_amount: Decimal


class CommissionExplanationQuery:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_receipt(self, receipt_id: int) -> list[ExplainedCalculation]:
        return await self._list(CommissionCalculationSnapshotModel.receipt_id == receipt_id)

    async def by_proposal(self, proposal_id: int) -> list[ExplainedCalculation]:
        return await self._list(CommissionCalculationSnapshotModel.proposal_id == proposal_id)

    async def _list(self, criterion: Any) -> list[ExplainedCalculation]:
        rows = (
            await self._session.execute(
                select(
                    CommissionCalculationSnapshotModel,
                    CollaboratorModel.full_name,
                    CommissionRuleSetModel.version,
                    CommissionStrategyConfigModel.version,
                )
                .join(
                    CollaboratorModel,
                    CollaboratorModel.id == CommissionCalculationSnapshotModel.beneficiary_id,
                )
                .outerjoin(
                    CommissionRuleSetModel,
                    CommissionRuleSetModel.id == CommissionCalculationSnapshotModel.rule_set_id,
                )
                .outerjoin(
                    CommissionStrategyConfigModel,
                    CommissionStrategyConfigModel.id
                    == CommissionCalculationSnapshotModel.strategy_config_id,
                )
                .where(criterion)
                .order_by(
                    CommissionCalculationSnapshotModel.competence_date,
                    CommissionCalculationSnapshotModel.id,
                )
            )
        ).all()
        if not rows:
            return []
        snapshots = [row[0] for row in rows]
        entries = list(
            (
                await self._session.scalars(
                    select(CommissionEntryModel)
                    .where(CommissionEntryModel.snapshot_id.in_([item.id for item in snapshots]))
                    .order_by(CommissionEntryModel.created_at, CommissionEntryModel.id)
                )
            ).all()
        )
        by_snapshot: dict[int, list[CommissionEntryModel]] = {}
        for entry in entries:
            by_snapshot.setdefault(entry.snapshot_id, []).append(entry)
        result: list[ExplainedCalculation] = []
        for snapshot, beneficiary_name, rule_version, config_version in rows:
            snapshot_entries = by_snapshot.get(snapshot.id, [])
            result.append(
                ExplainedCalculation(
                    id=snapshot.id,
                    proposal_id=snapshot.proposal_id,
                    receipt_id=snapshot.receipt_id,
                    beneficiary_id=snapshot.beneficiary_id,
                    beneficiary_name=str(beneficiary_name),
                    strategy=snapshot.strategy,
                    rule_version=rule_version or config_version,
                    competence_date=snapshot.competence_date,
                    inputs=dict(snapshot.inputs),
                    outputs=dict(snapshot.outputs),
                    calculated_at=snapshot.calculated_at,
                    entries=tuple(
                        ExplainedEntry(
                            id=item.id,
                            entry_type=item.entry_type,
                            amount=item.amount,
                            competence_date=item.competence_date,
                            description=item.description,
                            reversal_id=item.reversal_id,
                            created_at=item.created_at,
                        )
                        for item in snapshot_entries
                    ),
                    net_amount=sum((item.amount for item in snapshot_entries), Decimal("0")),
                )
            )
        return result
