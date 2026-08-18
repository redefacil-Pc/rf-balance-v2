"""Lançamentos manuais e ciclo financeiro dos fechamentos."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, or_, select

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commissions.domain.errors import CommissionRuleConfigurationError
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionEntryModel,
    CommissionManualEntryModel,
    CommissionPeriodModel,
    CommissionSettlementModel,
)
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.models.collaborator_role_model import (
    CollaboratorRoleModel,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

CENTAVO = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class SettlementView:
    model: CommissionSettlementModel
    beneficiary_name: str
    roles: tuple[str, ...]


class CommissionSettlementManager:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        audit: AuditRecorder,
        outbox: SqlOutboxRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._session = uow.session
        self._audit = audit
        self._outbox = outbox
        self._clock = clock

    async def add_bko_entry(
        self,
        *,
        beneficiary_id: int,
        amount: Decimal,
        effective_date: date,
        description: str,
        idempotency_key: str,
        actor: int,
        correlation_id: str | None,
    ) -> CommissionManualEntryModel:
        return await self._add_manual_entry(
            beneficiary_id=beneficiary_id,
            amount=amount,
            effective_date=effective_date,
            description=description,
            idempotency_key=idempotency_key,
            actor=actor,
            correlation_id=correlation_id,
            entry_type="BKO_COMMISSION",
            required_role="BKO",
            mei_only=True,
        )

    async def add_finalization_entry(
        self,
        *,
        beneficiary_id: int,
        amount: Decimal,
        effective_date: date,
        description: str,
        idempotency_key: str,
        actor: int,
        correlation_id: str | None,
    ) -> CommissionManualEntryModel:
        return await self._add_manual_entry(
            beneficiary_id=beneficiary_id,
            amount=amount,
            effective_date=effective_date,
            description=description,
            idempotency_key=idempotency_key,
            actor=actor,
            correlation_id=correlation_id,
            entry_type="FINALIZATION_BONUS",
            required_role="FINALIZACAO",
            mei_only=False,
        )

    async def _add_manual_entry(
        self,
        *,
        beneficiary_id: int,
        amount: Decimal,
        effective_date: date,
        description: str,
        idempotency_key: str,
        actor: int,
        correlation_id: str | None,
        entry_type: str,
        required_role: str,
        mei_only: bool,
    ) -> CommissionManualEntryModel:
        amount = amount.quantize(CENTAVO, rounding=ROUND_HALF_UP)
        if amount <= 0:
            raise CommissionRuleConfigurationError("O valor manual deve ser positivo.")
        if effective_date > self._clock.business_date():
            raise CommissionRuleConfigurationError("A data efetiva não pode estar no futuro.")
        collaborator = await self._session.get(CollaboratorModel, beneficiary_id)
        if collaborator is None:
            raise CommissionRuleConfigurationError("Colaborador não encontrado.")
        if (
            not collaborator.is_active
            or (mei_only and collaborator.tax_regime != "MEI")
            or not await self._has_role(beneficiary_id, required_role, effective_date)
        ):
            eligibility = "BKO ativo, MEI" if mei_only else "colaborador ativo"
            raise CommissionRuleConfigurationError(
                f"Somente {eligibility}, com função {required_role} vigente, "
                "recebe este lançamento."
            )
        existing = await self._session.scalar(
            select(CommissionManualEntryModel).where(
                CommissionManualEntryModel.created_by == actor,
                CommissionManualEntryModel.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing
        entry = CommissionManualEntryModel(
            beneficiary_id=beneficiary_id,
            entry_type=entry_type,
            amount=amount,
            effective_date=effective_date,
            description=description.strip(),
            idempotency_key=idempotency_key,
            created_by=actor,
        )
        self._session.add(entry)
        await self._session.flush()
        self._audit.registrar(
            module="commissions",
            action="commission.manual_entry_created",
            actor_user_id=actor,
            aggregate_type="commission_manual_entry",
            aggregate_id=str(entry.id),
            correlation_id=correlation_id,
            payload={
                "beneficiary_id": beneficiary_id,
                "amount": str(amount),
                "entry_type": entry_type,
            },
        )
        await self._uow.commit()
        return entry

    async def generate(
        self,
        *,
        period_start: date,
        period_end: date,
        actor: int,
        correlation_id: str | None,
    ) -> list[SettlementView]:
        self._validate_period(period_start, period_end)
        await self._ensure_open(period_start, period_end)
        automatic = (
            await self._session.execute(
                select(CommissionEntryModel.beneficiary_id, func.sum(CommissionEntryModel.amount))
                .where(
                    CommissionEntryModel.competence_date >= period_start,
                    CommissionEntryModel.competence_date <= period_end,
                )
                .group_by(CommissionEntryModel.beneficiary_id)
            )
        ).all()
        manual = (
            await self._session.execute(
                select(
                    CommissionManualEntryModel.beneficiary_id,
                    CommissionManualEntryModel.entry_type,
                    func.sum(CommissionManualEntryModel.amount),
                )
                .where(
                    CommissionManualEntryModel.effective_date >= period_start,
                    CommissionManualEntryModel.effective_date <= period_end,
                )
                .group_by(
                    CommissionManualEntryModel.beneficiary_id,
                    CommissionManualEntryModel.entry_type,
                )
            )
        ).all()
        gross_by_beneficiary: dict[int, Decimal] = {}
        for beneficiary_id, amount in automatic:
            gross_by_beneficiary[int(beneficiary_id)] = gross_by_beneficiary.get(
                int(beneficiary_id), Decimal("0")
            ) + Decimal(amount)
        bonus_by_beneficiary: dict[int, Decimal] = {}
        for beneficiary_id, entry_type, amount in manual:
            target = (
                bonus_by_beneficiary
                if entry_type == "FINALIZATION_BONUS"
                else gross_by_beneficiary
            )
            target[int(beneficiary_id)] = target.get(int(beneficiary_id), Decimal("0")) + Decimal(
                amount
            )
        for beneficiary_id in bonus_by_beneficiary:
            gross_by_beneficiary.setdefault(beneficiary_id, Decimal("0"))
        previous_rows = list(
            (
                await self._session.scalars(
                    select(CommissionSettlementModel)
                    .where(CommissionSettlementModel.period_end < period_start)
                    .order_by(
                        CommissionSettlementModel.beneficiary_id,
                        CommissionSettlementModel.period_end.desc(),
                    )
                )
            ).all()
        )
        latest_by_beneficiary: dict[int, CommissionSettlementModel] = {}
        for previous in previous_rows:
            latest_by_beneficiary.setdefault(previous.beneficiary_id, previous)
        for beneficiary_id, previous in latest_by_beneficiary.items():
            if previous.status == "DEFERRED" and previous.deferred_amount > 0:
                gross_by_beneficiary.setdefault(beneficiary_id, Decimal("0"))
        for beneficiary_id, gross in gross_by_beneficiary.items():
            settlement = await self._session.scalar(
                select(CommissionSettlementModel)
                .where(
                    CommissionSettlementModel.beneficiary_id == beneficiary_id,
                    CommissionSettlementModel.period_start == period_start,
                    CommissionSettlementModel.period_end == period_end,
                )
                .with_for_update()
            )
            if settlement is not None and settlement.status == "PAID":
                continue
            carryover = await self._carryover(beneficiary_id, period_start)
            if settlement is None:
                settlement = CommissionSettlementModel(
                    beneficiary_id=beneficiary_id,
                    period_start=period_start,
                    period_end=period_end,
                    gross_amount=gross.quantize(CENTAVO),
                    carryover_amount=carryover,
                    bonus_amount=bonus_by_beneficiary.get(beneficiary_id, Decimal("0")).quantize(
                        CENTAVO
                    ),
                    discount_amount=Decimal("0.00"),
                    deferred_amount=Decimal("0.00"),
                    paid_amount=Decimal("0.00"),
                    payable_amount=Decimal("0.00"),
                    status="PENDING",
                    created_by=actor,
                    updated_by=actor,
                )
                self._session.add(settlement)
            else:
                settlement.gross_amount = gross.quantize(CENTAVO)
                settlement.carryover_amount = carryover
                if beneficiary_id in bonus_by_beneficiary:
                    settlement.bonus_amount = bonus_by_beneficiary[beneficiary_id].quantize(CENTAVO)
                settlement.updated_by = actor
            self._recalculate(settlement)
        await self._session.flush()
        self._audit.registrar(
            module="commissions",
            action="commission.settlements_generated",
            actor_user_id=actor,
            aggregate_type="commission_settlement_period",
            aggregate_id=f"{period_start}:{period_end}",
            correlation_id=correlation_id,
            payload={"beneficiaries": len(gross_by_beneficiary)},
        )
        await self._uow.commit()
        return await self.list(period_start=period_start, period_end=period_end)

    async def list(self, *, period_start: date, period_end: date) -> list[SettlementView]:
        rows = (
            await self._session.execute(
                select(CommissionSettlementModel, CollaboratorModel.full_name)
                .join(
                    CollaboratorModel,
                    CollaboratorModel.id == CommissionSettlementModel.beneficiary_id,
                )
                .where(
                    CommissionSettlementModel.period_start == period_start,
                    CommissionSettlementModel.period_end == period_end,
                )
                .order_by(CollaboratorModel.full_name)
            )
        ).all()
        roles = await self._roles_for(
            [int(row[0].beneficiary_id) for row in rows], period_start, period_end
        )
        return [
            SettlementView(
                model=row[0],
                beneficiary_name=str(row[1]),
                roles=roles.get(int(row[0].beneficiary_id), ()),
            )
            for row in rows
        ]

    async def adjust(
        self,
        *,
        settlement_id: int,
        bonus_amount: Decimal,
        discount_amount: Decimal,
        deferred_amount: Decimal,
        notes: str | None,
        actor: int,
        correlation_id: str | None,
    ) -> SettlementView:
        settlement = await self._locked(settlement_id)
        await self._ensure_open(settlement.period_start, settlement.period_end)
        if settlement.status == "PAID":
            raise CommissionRuleConfigurationError("Fechamento pago não pode ser alterado.")
        amounts = [bonus_amount, discount_amount, deferred_amount]
        if any(value < 0 for value in amounts):
            raise CommissionRuleConfigurationError("Ajustes não podem ser negativos.")
        settlement.bonus_amount = bonus_amount.quantize(CENTAVO)
        settlement.discount_amount = discount_amount.quantize(CENTAVO)
        settlement.deferred_amount = deferred_amount.quantize(CENTAVO)
        available = (
            settlement.gross_amount
            + settlement.carryover_amount
            + settlement.bonus_amount
            - settlement.paid_amount
        )
        if settlement.discount_amount + settlement.deferred_amount > available:
            raise CommissionRuleConfigurationError(
                "Desconto e adiamento não podem exceder o saldo bruto disponível."
            )
        settlement.notes = notes.strip() if notes else None
        settlement.updated_by = actor
        self._recalculate(settlement)
        await self._record_change(
            settlement, "commission.settlement_adjusted", actor, correlation_id
        )
        return await self._view(settlement)

    async def pay(
        self,
        *,
        settlement_id: int,
        amount: Decimal,
        payment_date: date,
        payment_method: str,
        reference: str | None,
        actor: int,
        correlation_id: str | None,
    ) -> SettlementView:
        settlement = await self._locked(settlement_id)
        amount = amount.quantize(CENTAVO)
        if settlement.status == "PAID" or amount <= 0 or amount > settlement.payable_amount:
            raise CommissionRuleConfigurationError("Valor de pagamento inválido para o saldo.")
        if payment_date > self._clock.business_date():
            raise CommissionRuleConfigurationError("A data do pagamento não pode estar no futuro.")
        settlement.paid_amount += amount
        settlement.payment_date = payment_date
        settlement.payment_method = payment_method.strip().upper()
        settlement.payment_reference = reference.strip() if reference else None
        settlement.updated_by = actor
        self._recalculate(settlement)
        await self._record_change(settlement, "commission.settlement_paid", actor, correlation_id)
        return await self._view(settlement)

    async def _record_change(
        self,
        settlement: CommissionSettlementModel,
        action: str,
        actor: int,
        correlation_id: str | None,
    ) -> None:
        await self._session.flush()
        payload = {
            "status": settlement.status,
            "payable_amount": str(settlement.payable_amount),
            "paid_amount": str(settlement.paid_amount),
            "deferred_amount": str(settlement.deferred_amount),
        }
        self._audit.registrar(
            module="commissions",
            action=action,
            actor_user_id=actor,
            aggregate_type="commission_settlement",
            aggregate_id=str(settlement.id),
            correlation_id=correlation_id,
            payload=payload,
        )
        self._outbox.registrar(
            event_type=f"{action}.v1",
            aggregate_type="commission_settlement",
            aggregate_id=str(settlement.id),
            correlation_id=correlation_id,
            payload=payload,
        )
        await self._uow.commit()

    async def _carryover(self, beneficiary_id: int, period_start: date) -> Decimal:
        previous = await self._session.scalar(
            select(CommissionSettlementModel)
            .where(
                CommissionSettlementModel.beneficiary_id == beneficiary_id,
                CommissionSettlementModel.period_end < period_start,
            )
            .order_by(CommissionSettlementModel.period_end.desc())
            .limit(1)
        )
        if previous is None or previous.status != "DEFERRED":
            return Decimal("0.00")
        return previous.deferred_amount

    async def _ensure_open(self, period_start: date, period_end: date) -> None:
        closed = await self._session.scalar(
            select(CommissionPeriodModel.id).where(
                CommissionPeriodModel.period_start == period_start,
                CommissionPeriodModel.period_end == period_end,
                CommissionPeriodModel.status == "CLOSED",
            )
        )
        if closed is not None:
            raise CommissionRuleConfigurationError(
                "O período está fechado e seus cálculos não podem ser alterados."
            )

    async def _locked(self, settlement_id: int) -> CommissionSettlementModel:
        settlement = await self._session.scalar(
            select(CommissionSettlementModel)
            .where(CommissionSettlementModel.id == settlement_id)
            .with_for_update()
        )
        if settlement is None:
            raise CommissionRuleConfigurationError("Fechamento não encontrado.")
        return settlement

    async def _view(self, settlement: CommissionSettlementModel) -> SettlementView:
        beneficiary = await self._session.get(CollaboratorModel, settlement.beneficiary_id)
        assert beneficiary is not None
        roles = await self._roles_for(
            [settlement.beneficiary_id], settlement.period_start, settlement.period_end
        )
        return SettlementView(
            settlement, beneficiary.full_name, roles.get(settlement.beneficiary_id, ())
        )

    async def _roles_for(
        self, beneficiary_ids: Sequence[int], period_start: date, period_end: date
    ) -> dict[int, tuple[str, ...]]:
        if not beneficiary_ids:
            return {}
        rows = (
            await self._session.execute(
                select(CollaboratorRoleModel.collaborator_id, CollaboratorRoleModel.role).where(
                    CollaboratorRoleModel.collaborator_id.in_(beneficiary_ids),
                    CollaboratorRoleModel.valid_from <= period_end,
                    or_(
                        CollaboratorRoleModel.valid_to.is_(None),
                        CollaboratorRoleModel.valid_to >= period_start,
                    ),
                )
            )
        ).all()
        result: dict[int, set[str]] = {}
        for beneficiary_id, role in rows:
            result.setdefault(int(beneficiary_id), set()).add(str(role))
        return {
            beneficiary_id: tuple(sorted(beneficiary_roles))
            for beneficiary_id, beneficiary_roles in result.items()
        }

    async def _has_role(self, collaborator_id: int, role: str, reference: date) -> bool:
        return (
            await self._session.scalar(
                select(CollaboratorRoleModel.id).where(
                    CollaboratorRoleModel.collaborator_id == collaborator_id,
                    CollaboratorRoleModel.role == role,
                    CollaboratorRoleModel.valid_from <= reference,
                    or_(
                        CollaboratorRoleModel.valid_to.is_(None),
                        CollaboratorRoleModel.valid_to >= reference,
                    ),
                )
            )
            is not None
        )

    @staticmethod
    def _recalculate(settlement: CommissionSettlementModel) -> None:
        settlement.payable_amount = max(
            settlement.gross_amount
            + settlement.carryover_amount
            + settlement.bonus_amount
            - settlement.discount_amount
            - settlement.deferred_amount
            - settlement.paid_amount,
            Decimal("0.00"),
        ).quantize(CENTAVO)
        if settlement.deferred_amount > 0:
            settlement.status = "DEFERRED"
        elif settlement.payable_amount == 0 and settlement.paid_amount > 0:
            settlement.status = "PAID"
        else:
            settlement.status = "PENDING"

    @staticmethod
    def _validate_period(period_start: date, period_end: date) -> None:
        if period_end < period_start:
            raise CommissionRuleConfigurationError("O fim do período deve ser posterior ao início.")
        if (period_end - period_start).days > 92:
            raise CommissionRuleConfigurationError("O período não pode ultrapassar 93 dias.")
