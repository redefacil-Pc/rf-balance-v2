from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import or_, select

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commissions.domain.errors import (
    CommissionRuleConfigurationError,
    CommissionRuleConflictError,
    CommissionRuleSetNotFoundError,
)
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionStrategyConfigModel,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

STRATEGIES = frozenset(
    {
        "SCALED_CONSULTANT",
        "COMMERCIAL_LEADER",
        "GENERAL_MEI_LEADER",
        "FINALIZER",
        "FINALIZATION_LEADER",
    }
)


def _decimal(value: object, field: str, *, maximum: Decimal | None = None) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CommissionRuleConfigurationError(f"{field} deve ser numérico.") from exc
    if number < 0 or (maximum is not None and number > maximum):
        raise CommissionRuleConfigurationError(f"{field} está fora do intervalo permitido.")
    return number


def validate_strategy_config(strategy: str, config: dict[str, Any]) -> None:
    if strategy not in STRATEGIES:
        raise CommissionRuleConfigurationError("Estratégia de comissão desconhecida.")
    if strategy == "SCALED_CONSULTANT":
        ranges = config.get("production_ranges")
        if not isinstance(ranges, list) or len(ranges) < 1:
            raise CommissionRuleConfigurationError(
                "Informe as faixas de produção do MEI Escalonado."
            )
        expected = Decimal("0")
        for index, item in enumerate(ranges):
            if not isinstance(item, dict):
                raise CommissionRuleConfigurationError("Faixa de produção inválida.")
            minimum = _decimal(item.get("min"), "Produção mínima")
            if minimum != expected:
                raise CommissionRuleConfigurationError(
                    "As faixas de produção devem ser contínuas e iniciar em zero."
                )
            percentages = item.get("percentages")
            if not isinstance(percentages, list) or len(percentages) != 4:
                raise CommissionRuleConfigurationError(
                    "Cada faixa deve ter quatro percentuais de TPS."
                )
            for percentage in percentages:
                _decimal(percentage, "Percentual", maximum=Decimal("100"))
            maximum = item.get("max")
            last = index == len(ranges) - 1
            if last and maximum is not None:
                raise CommissionRuleConfigurationError(
                    "A última faixa de produção deve ficar sem limite."
                )
            if not last:
                expected = _decimal(maximum, "Produção máxima")
                if expected <= minimum:
                    raise CommissionRuleConfigurationError(
                        "O fim da faixa de produção deve ser maior que o início."
                    )
        if config.get("display_mode") not in {"WEEKLY", "MONTHLY"}:
            raise CommissionRuleConfigurationError("Modo deve ser WEEKLY ou MONTHLY.")
        tps_ranges = config.get("tps_ranges")
        if not isinstance(tps_ranges, list) or len(tps_ranges) != 4:
            raise CommissionRuleConfigurationError("Informe as quatro faixas TPS do Escalonado.")
        ordenadas = sorted(
            tps_ranges,
            key=lambda item: _decimal(item.get("min"), "TPS mínimo")
            if isinstance(item, dict)
            else Decimal("-1"),
        )
        expected_tps = Decimal("0")
        for index, item in enumerate(ordenadas):
            if not isinstance(item, dict):
                raise CommissionRuleConfigurationError("Faixa TPS inválida.")
            minimum_tps = _decimal(item.get("min"), "TPS mínimo", maximum=Decimal("100"))
            if minimum_tps != expected_tps:
                raise CommissionRuleConfigurationError(
                    "As faixas TPS devem ser contínuas e iniciar em zero."
                )
            maximum = item.get("max")
            last = index == len(ordenadas) - 1
            if last and maximum is not None:
                raise CommissionRuleConfigurationError("A última faixa TPS deve ficar sem limite.")
            if not last:
                expected_tps = _decimal(maximum, "TPS máximo", maximum=Decimal("100"))
                if expected_tps <= minimum_tps:
                    raise CommissionRuleConfigurationError(
                        "O fim da faixa TPS deve ser maior que o início."
                    )
    elif strategy == "COMMERCIAL_LEADER":
        _decimal(config.get("mei_min_tps"), "TPS mínimo", maximum=Decimal("100"))
        _decimal(config.get("mei_percentage"), "Percentual MEI", maximum=Decimal("100"))
        _decimal(config.get("clt_percentage"), "Percentual CLT", maximum=Decimal("100"))
    elif strategy == "GENERAL_MEI_LEADER":
        _decimal(config.get("base_percentage"), "Percentual da base", maximum=Decimal("100"))
        tiers = config.get("tiers")
        if not isinstance(tiers, list) or not tiers:
            raise CommissionRuleConfigurationError("Informe os níveis do líder MEI geral.")
        expected = Decimal("0")
        for item in tiers:
            if (
                not isinstance(item, dict)
                or _decimal(item.get("min"), "Produção mínima") != expected
            ):
                raise CommissionRuleConfigurationError(
                    "Os níveis devem ser contínuos e iniciar em zero."
                )
            expected = _decimal(item.get("max"), "Produção máxima")
            _decimal(item.get("percentage"), "Percentual", maximum=Decimal("100"))
    elif strategy == "FINALIZER":
        _decimal(config.get("threshold_amount"), "Gatilho")
        _decimal(config.get("fixed_amount"), "Valor fixo")
        _decimal(config.get("excess_percentage"), "Percentual do excedente", maximum=Decimal("100"))
    else:
        _decimal(config.get("mei_percentage"), "Percentual MEI", maximum=Decimal("100"))
        _decimal(config.get("clt_percentage"), "Percentual CLT", maximum=Decimal("100"))


class CommissionStrategyConfigManager:
    def __init__(
        self, *, uow: UnitOfWork, audit: AuditRecorder, outbox: SqlOutboxRecorder, clock: Clock
    ) -> None:
        self._uow = uow
        self._session = uow.session
        self._audit = audit
        self._outbox = outbox
        self._clock = clock

    async def listar(self) -> list[CommissionStrategyConfigModel]:
        return list(
            (
                await self._session.scalars(
                    select(CommissionStrategyConfigModel).order_by(
                        CommissionStrategyConfigModel.strategy,
                        CommissionStrategyConfigModel.valid_from.desc(),
                    )
                )
            ).all()
        )

    async def create(
        self,
        *,
        strategy: str,
        version: str,
        name: str,
        valid_from: date,
        reason: str,
        config: dict[str, Any],
        actor: int,
        correlation_id: str | None,
    ) -> CommissionStrategyConfigModel:
        if valid_from <= self._clock.business_date():
            raise CommissionRuleConfigurationError("Uma nova versão deve iniciar em data futura.")
        validate_strategy_config(strategy, config)
        exists = await self._session.scalar(
            select(CommissionStrategyConfigModel.id).where(
                CommissionStrategyConfigModel.strategy == strategy,
                CommissionStrategyConfigModel.version == version.strip(),
            )
        )
        if exists is not None:
            raise CommissionRuleConflictError(f"A versão {version} já existe para essa estratégia.")
        model = CommissionStrategyConfigModel(
            strategy=strategy,
            version=version.strip(),
            name=name.strip(),
            status="DRAFT",
            valid_from=valid_from,
            valid_to=None,
            config=config,
            reason=reason.strip(),
            created_by=actor,
        )
        self._session.add(model)
        await self._session.flush()
        self._audit.registrar(
            module="commissions",
            action="commission_strategy_config.created",
            actor_user_id=actor,
            aggregate_type="commission_strategy_config",
            aggregate_id=str(model.id),
            correlation_id=correlation_id,
            payload={
                "strategy": strategy,
                "version": model.version,
                "valid_from": valid_from.isoformat(),
            },
        )
        await self._uow.commit()
        return model

    async def activate(
        self, *, config_id: int, reason: str, actor: int, correlation_id: str | None
    ) -> CommissionStrategyConfigModel:
        model = await self._session.scalar(
            select(CommissionStrategyConfigModel)
            .where(CommissionStrategyConfigModel.id == config_id)
            .with_for_update()
        )
        if model is None:
            raise CommissionRuleSetNotFoundError(f"Configuração {config_id} não encontrada.")
        if model.status != "DRAFT":
            raise CommissionRuleConflictError("Somente um rascunho pode ser ativado.")
        if model.valid_from <= self._clock.business_date():
            raise CommissionRuleConfigurationError("A ativação precisa ocorrer antes da vigência.")
        next_model = await self._session.scalar(
            select(CommissionStrategyConfigModel)
            .where(
                CommissionStrategyConfigModel.strategy == model.strategy,
                CommissionStrategyConfigModel.status == "ACTIVE",
                CommissionStrategyConfigModel.valid_from >= model.valid_from,
            )
            .order_by(CommissionStrategyConfigModel.valid_from)
            .with_for_update()
            .limit(1)
        )
        if next_model is not None and next_model.valid_from == model.valid_from:
            raise CommissionRuleConflictError("Já existe uma versão ativa iniciando nessa data.")
        previous = list(
            (
                await self._session.scalars(
                    select(CommissionStrategyConfigModel)
                    .where(
                        CommissionStrategyConfigModel.strategy == model.strategy,
                        CommissionStrategyConfigModel.status == "ACTIVE",
                        CommissionStrategyConfigModel.valid_from < model.valid_from,
                        or_(
                            CommissionStrategyConfigModel.valid_to.is_(None),
                            CommissionStrategyConfigModel.valid_to >= model.valid_from,
                        ),
                    )
                    .with_for_update()
                )
            ).all()
        )
        for item in previous:
            item.valid_to = model.valid_from - timedelta(days=1)
        model.status = "ACTIVE"
        model.valid_to = None if next_model is None else next_model.valid_from - timedelta(days=1)
        model.activated_at = self._clock.now()
        model.activated_by = actor
        self._audit.registrar(
            module="commissions",
            action="commission_strategy_config.activated",
            actor_user_id=actor,
            aggregate_type="commission_strategy_config",
            aggregate_id=str(model.id),
            correlation_id=correlation_id,
            payload={
                "strategy": model.strategy,
                "version": model.version,
                "reason": reason.strip(),
            },
        )
        self._outbox.registrar(
            event_type="commission.strategy_config_activated.v1",
            aggregate_type="commission_strategy_config",
            aggregate_id=str(model.id),
            correlation_id=correlation_id,
            payload={
                "strategy": model.strategy,
                "version": model.version,
                "valid_from": model.valid_from.isoformat(),
            },
        )
        await self._uow.commit()
        return model
