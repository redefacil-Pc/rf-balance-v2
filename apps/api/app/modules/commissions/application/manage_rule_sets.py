from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import or_, select

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commissions.domain.errors import (
    CommissionRuleConfigurationError,
    CommissionRuleConflictError,
    CommissionRuleSetNotFoundError,
)
from app.modules.commissions.domain.standard_consultant import (
    ConfiguracaoDeComissaoInvalidaError,
    FaixaConsultorPadrao,
    validar_faixas,
)
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionRuleModel,
    CommissionRuleSetModel,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

ESTRATEGIA = "STANDARD_CONSULTANT"


class CommissionRuleSetManager:
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

    async def listar(self) -> list[tuple[CommissionRuleSetModel, list[CommissionRuleModel]]]:
        conjuntos = list(
            (
                await self._session.scalars(
                    select(CommissionRuleSetModel)
                    .where(CommissionRuleSetModel.strategy == ESTRATEGIA)
                    .order_by(
                        CommissionRuleSetModel.valid_from.desc(),
                        CommissionRuleSetModel.id.desc(),
                    )
                )
            ).all()
        )
        if not conjuntos:
            return []
        regras = list(
            (
                await self._session.scalars(
                    select(CommissionRuleModel)
                    .where(
                        CommissionRuleModel.rule_set_id.in_([item.id for item in conjuntos]),
                        CommissionRuleModel.tax_regime == "MEI",
                    )
                    .order_by(
                        CommissionRuleModel.rule_set_id,
                        CommissionRuleModel.tax_regime,
                        CommissionRuleModel.sort_order,
                    )
                )
            ).all()
        )
        por_conjunto: dict[int, list[CommissionRuleModel]] = {}
        for regra in regras:
            por_conjunto.setdefault(regra.rule_set_id, []).append(regra)
        return [(item, por_conjunto.get(item.id, [])) for item in conjuntos]

    async def create(
        self,
        *,
        version: str,
        name: str,
        valid_from: date,
        reason: str,
        rules: list[tuple[str, Decimal, Decimal | None, Decimal]],
        actor: int,
        correlation_id: str | None,
    ) -> CommissionRuleSetModel:
        if valid_from <= self._clock.business_date():
            raise CommissionRuleConfigurationError("Uma nova versão deve iniciar em data futura.")
        existente = await self._session.scalar(
            select(CommissionRuleSetModel.id).where(
                CommissionRuleSetModel.strategy == ESTRATEGIA,
                CommissionRuleSetModel.version == version.strip(),
            )
        )
        if existente is not None:
            raise CommissionRuleConflictError(f"A versão {version} já existe.")
        faixas = [
            FaixaConsultorPadrao(indice, regime, minimo, maximo, percentual)
            for indice, (regime, minimo, maximo, percentual) in enumerate(rules, 1)
        ]
        try:
            validar_faixas(faixas, "MEI")
        except ConfiguracaoDeComissaoInvalidaError as exc:
            raise CommissionRuleConfigurationError(str(exc)) from exc

        conjunto = CommissionRuleSetModel(
            strategy=ESTRATEGIA,
            version=version.strip(),
            name=name.strip(),
            status="DRAFT",
            valid_from=valid_from,
            valid_to=None,
            reason=reason.strip(),
            created_by=actor,
        )
        self._session.add(conjunto)
        await self._session.flush()
        ordenacao = {"MEI": 0}
        for regime, minimo, maximo, percentual in rules:
            ordenacao[regime] += 1
            self._session.add(
                CommissionRuleModel(
                    rule_set_id=conjunto.id,
                    role="CONSULTOR",
                    tax_regime=regime,
                    tps_min=minimo,
                    tps_max=maximo,
                    percentage=percentual,
                    sort_order=ordenacao[regime],
                    parameters={},
                )
            )
        self._audit.registrar(
            module="commissions",
            action="commission_rule_set.created",
            actor_user_id=actor,
            aggregate_type="commission_rule_set",
            aggregate_id=str(conjunto.id),
            correlation_id=correlation_id,
            payload={"version": conjunto.version, "valid_from": valid_from.isoformat()},
        )
        await self._uow.commit()
        return conjunto

    async def activate(
        self,
        *,
        rule_set_id: int,
        reason: str,
        actor: int,
        correlation_id: str | None,
    ) -> CommissionRuleSetModel:
        conjunto = await self._session.scalar(
            select(CommissionRuleSetModel)
            .where(CommissionRuleSetModel.id == rule_set_id)
            .with_for_update()
        )
        if conjunto is None:
            raise CommissionRuleSetNotFoundError(f"Versão {rule_set_id} não encontrada.")
        if conjunto.status != "DRAFT":
            raise CommissionRuleConflictError("Somente uma versão em rascunho pode ser ativada.")
        if conjunto.valid_from <= self._clock.business_date():
            raise CommissionRuleConfigurationError(
                "A ativação precisa ocorrer antes do início da vigência."
            )
        proxima = await self._session.scalar(
            select(CommissionRuleSetModel)
            .where(
                CommissionRuleSetModel.strategy == conjunto.strategy,
                CommissionRuleSetModel.status == "ACTIVE",
                CommissionRuleSetModel.valid_from >= conjunto.valid_from,
            )
            .order_by(CommissionRuleSetModel.valid_from)
            .with_for_update()
            .limit(1)
        )
        if proxima is not None and proxima.valid_from == conjunto.valid_from:
            raise CommissionRuleConflictError("Já existe uma versão ativa iniciando nessa data.")
        anteriores = list(
            (
                await self._session.scalars(
                    select(CommissionRuleSetModel)
                    .where(
                        CommissionRuleSetModel.strategy == conjunto.strategy,
                        CommissionRuleSetModel.status == "ACTIVE",
                        CommissionRuleSetModel.valid_from < conjunto.valid_from,
                        or_(
                            CommissionRuleSetModel.valid_to.is_(None),
                            CommissionRuleSetModel.valid_to >= conjunto.valid_from,
                        ),
                    )
                    .with_for_update()
                )
            ).all()
        )
        for anterior in anteriores:
            anterior.valid_to = conjunto.valid_from - timedelta(days=1)
        conjunto.status = "ACTIVE"
        conjunto.valid_to = None if proxima is None else proxima.valid_from - timedelta(days=1)
        conjunto.activated_at = self._clock.now()
        conjunto.activated_by = actor
        self._audit.registrar(
            module="commissions",
            action="commission_rule_set.activated",
            actor_user_id=actor,
            aggregate_type="commission_rule_set",
            aggregate_id=str(conjunto.id),
            correlation_id=correlation_id,
            payload={
                "version": conjunto.version,
                "valid_from": conjunto.valid_from.isoformat(),
                "reason": reason.strip(),
                "closed_rule_sets": [item.id for item in anteriores],
            },
        )
        self._outbox.registrar(
            event_type="commission.rule_set_activated.v1",
            aggregate_type="commission_rule_set",
            aggregate_id=str(conjunto.id),
            correlation_id=correlation_id,
            payload={"version": conjunto.version, "valid_from": conjunto.valid_from.isoformat()},
        )
        await self._uow.commit()
        return conjunto
