from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import and_, select

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commissions.domain.errors import (
    CommissionRuleConfigurationError,
    CommissionRuleConflictError,
)
from app.modules.commissions.infrastructure.models.commission_models import CommissionPeriodModel
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock


class CommissionPeriodManager:
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

    async def list(self) -> list[CommissionPeriodModel]:
        return list(
            (
                await self._session.scalars(
                    select(CommissionPeriodModel).order_by(
                        CommissionPeriodModel.period_start.desc()
                    )
                )
            ).all()
        )

    async def create(
        self,
        *,
        period_start: date,
        period_end: date,
        cutoff_at: datetime,
        reason: str,
        actor: int,
        correlation_id: str | None,
    ) -> CommissionPeriodModel:
        if period_end < period_start or (period_end - period_start).days > 92:
            raise CommissionRuleConfigurationError("Informe um período válido de até 93 dias.")
        if cutoff_at.tzinfo is None:
            raise CommissionRuleConfigurationError("O cutoff deve incluir o fuso horário.")
        overlap = await self._session.scalar(
            select(CommissionPeriodModel.id).where(
                and_(
                    CommissionPeriodModel.period_start <= period_end,
                    CommissionPeriodModel.period_end >= period_start,
                )
            )
        )
        if overlap is not None:
            raise CommissionRuleConflictError("Já existe um período sobreposto a essas datas.")
        model = CommissionPeriodModel(
            period_start=period_start,
            period_end=period_end,
            cutoff_at=cutoff_at,
            status="OPEN",
            reason=reason.strip(),
            created_by=actor,
        )
        self._session.add(model)
        await self._session.flush()
        self._audit.registrar(
            module="commissions",
            action="commission.period_created",
            actor_user_id=actor,
            aggregate_type="commission_period",
            aggregate_id=str(model.id),
            correlation_id=correlation_id,
            payload={
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "cutoff_at": cutoff_at.isoformat(),
            },
        )
        await self._uow.commit()
        await self._session.refresh(model)
        return model

    async def close(
        self,
        *,
        period_id: int,
        reason: str,
        actor: int,
        correlation_id: str | None,
    ) -> CommissionPeriodModel:
        model = await self._session.scalar(
            select(CommissionPeriodModel)
            .where(CommissionPeriodModel.id == period_id)
            .with_for_update()
        )
        if model is None:
            raise CommissionRuleConfigurationError("Período não encontrado.")
        if model.status != "OPEN":
            raise CommissionRuleConflictError("Este período já foi fechado.")
        if self._clock.now() < model.cutoff_at:
            raise CommissionRuleConfigurationError("O período só pode fechar após o cutoff.")
        model.status = "CLOSED"
        model.closed_at = self._clock.now()
        model.closed_by = actor
        self._audit.registrar(
            module="commissions",
            action="commission.period_closed",
            actor_user_id=actor,
            aggregate_type="commission_period",
            aggregate_id=str(model.id),
            correlation_id=correlation_id,
            payload={"reason": reason.strip()},
        )
        self._outbox.registrar(
            event_type="commission.period_closed.v1",
            aggregate_type="commission_period",
            aggregate_id=str(model.id),
            correlation_id=correlation_id,
            payload={
                "period_start": model.period_start.isoformat(),
                "period_end": model.period_end.isoformat(),
            },
        )
        await self._uow.commit()
        await self._session.refresh(model)
        return model
