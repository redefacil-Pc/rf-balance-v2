"""Materializa a comissão mensal marginal do Consultor Escalonado."""

from __future__ import annotations

import hashlib
import json
from calendar import monthrange
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commissions.domain.scaled_consultant import (
    CalculoConsultorEscalonado,
    FaixaProducaoEscalonada,
    FaixaTpsEscalonada,
    calcular_consultor_escalonado,
)
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionBeneficiaryPolicyModel,
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
    CommissionStrategyConfigModel,
)
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.models.collaborator_role_model import (
    CollaboratorRoleModel,
)
from app.modules.receivables.infrastructure.models.receipt_model import (
    ReceiptModel,
    ReceiptReversalModel,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder

ESTRATEGIA = "SCALED_CONSULTANT"
PAPEL = "CONSULTOR_MEI_ESCALONADO"
CENTAVO = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class _Contexto:
    recebimento: ReceiptModel
    proposta: ProposalModel
    base_elegivel: Decimal


@dataclass(frozen=True, slots=True)
class _Resultado:
    contexto: _Contexto
    configuracao: CommissionStrategyConfigModel
    calculo: CalculoConsultorEscalonado


class ScaledCommissionEngine:
    def __init__(self, session: AsyncSession, outbox: SqlOutboxRecorder | None = None) -> None:
        self._session = session
        self._outbox = outbox

    @property
    def _saida(self) -> SqlOutboxRecorder:
        """Outbox obrigatório para escrever; leitura pura dispensa."""
        if self._outbox is None:
            raise RuntimeError("Motor criado apenas para leitura não registra evento.")
        return self._outbox

    async def gerar_para_proposta(
        self, proposal_id: int, *, correlation_id: str | None
    ) -> list[int]:
        proposta = await self._session.get(ProposalModel, proposal_id)
        if proposta is None:
            return []
        consultor = await self._session.scalar(
            select(CollaboratorModel)
            .where(CollaboratorModel.id == proposta.consultant_id)
            .with_for_update()
        )
        if consultor is None:
            return []
        recebimentos = list(
            (
                await self._session.scalars(
                    select(ReceiptModel).where(
                        ReceiptModel.proposal_id == proposal_id,
                        ReceiptModel.status == "APPROVED",
                    )
                )
            ).all()
        )
        meses = sorted(
            {(item.business_date.year, item.business_date.month) for item in recebimentos}
        )
        criadas: list[int] = []
        for ano, mes in meses:
            criadas.extend(
                await self._materializar_mes(consultor.id, ano, mes, correlation_id=correlation_id)
            )
        return criadas

    async def possui_credito(self, receipt_id: int) -> bool:
        return (
            await self._session.scalar(
                select(CommissionEntryModel.id)
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .where(
                    CommissionEntryModel.receipt_id == receipt_id,
                    CommissionEntryModel.entry_type == "CREDIT",
                    CommissionCalculationSnapshotModel.strategy == ESTRATEGIA,
                )
                .limit(1)
            )
            is not None
        )

    async def estornar(self, reversal_id: int, *, correlation_id: str | None) -> int | None:
        estorno = await self._session.get(ReceiptReversalModel, reversal_id)
        if estorno is None:
            return None
        existente = await self._session.scalar(
            select(CommissionEntryModel.id)
            .join(
                CommissionCalculationSnapshotModel,
                CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
            )
            .where(
                CommissionEntryModel.reversal_id == reversal_id,
                CommissionCalculationSnapshotModel.strategy == ESTRATEGIA,
            )
        )
        if existente is not None:
            return existente
        credito = await self._session.scalar(
            select(CommissionEntryModel)
            .join(
                CommissionCalculationSnapshotModel,
                CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
            )
            .where(
                CommissionEntryModel.receipt_id == estorno.receipt_id,
                CommissionEntryModel.entry_type == "CREDIT",
                CommissionCalculationSnapshotModel.strategy == ESTRATEGIA,
            )
            .limit(1)
        )
        if credito is None:
            return None
        snapshot = await self._session.get(CommissionCalculationSnapshotModel, credito.snapshot_id)
        if snapshot is None:
            return None
        await self._session.scalar(
            select(CollaboratorModel)
            .where(CollaboratorModel.id == credito.beneficiary_id)
            .with_for_update()
        )
        resultados = await self._simular_mes(
            credito.beneficiary_id,
            snapshot.competence_date.year,
            snapshot.competence_date.month,
        )
        ideal = sum((item.calculo.comissao for item in resultados), Decimal("0"))
        inicio, fim = _limites_mes(snapshot.competence_date.year, snapshot.competence_date.month)
        atual = Decimal(
            await self._session.scalar(
                select(func.coalesce(func.sum(CommissionEntryModel.amount), 0))
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .where(
                    CommissionCalculationSnapshotModel.strategy == ESTRATEGIA,
                    CommissionCalculationSnapshotModel.beneficiary_id == credito.beneficiary_id,
                    CommissionCalculationSnapshotModel.competence_date >= inicio,
                    CommissionCalculationSnapshotModel.competence_date <= fim,
                )
            )
            or 0
        )
        diferenca = (ideal - atual).quantize(CENTAVO)
        if diferenca > 0:
            raise RuntimeError("Estorno escalonado não pode aumentar a comissão do mês.")
        lancamento = CommissionEntryModel(
            snapshot_id=credito.snapshot_id,
            proposal_id=credito.proposal_id,
            receipt_id=credito.receipt_id,
            reversal_id=estorno.id,
            beneficiary_id=credito.beneficiary_id,
            entry_type="DEBIT",
            amount=diferenca,
            competence_date=estorno.business_date,
            description=f"Recálculo mensal do Escalonado — estorno {estorno.id}",
        )
        self._session.add(lancamento)
        await self._session.flush()
        self._saida.registrar(
            event_type="commission.entry_reversed.v1",
            aggregate_type="commission_entry",
            aggregate_id=str(lancamento.id),
            correlation_id=correlation_id,
            payload={
                "strategy": ESTRATEGIA,
                "receipt_id": credito.receipt_id,
                "reversal_id": estorno.id,
                "beneficiary_id": credito.beneficiary_id,
                "amount": str(diferenca),
                "monthly_commission_before": str(atual),
                "monthly_commission_after": str(ideal),
            },
        )
        return lancamento.id

    async def _materializar_mes(
        self,
        collaborator_id: int,
        ano: int,
        mes: int,
        *,
        correlation_id: str | None,
    ) -> list[int]:
        consultor = await self._session.get(CollaboratorModel, collaborator_id)
        if consultor is None:
            return []
        resultados = await self._simular_mes(collaborator_id, ano, mes)
        existentes = set(
            (
                await self._session.scalars(
                    select(CommissionCalculationSnapshotModel.receipt_id).where(
                        CommissionCalculationSnapshotModel.beneficiary_id == collaborator_id,
                        CommissionCalculationSnapshotModel.strategy == ESTRATEGIA,
                    )
                )
            ).all()
        )
        criadas: list[int] = []
        for resultado in resultados:
            recebimento = resultado.contexto.recebimento
            proposta = resultado.contexto.proposta
            calculo = resultado.calculo
            config = resultado.configuracao
            policy = await self._policy(collaborator_id, recebimento.business_date)
            if recebimento.id in existentes:
                continue
            entradas = {
                "proposal_id": proposta.id,
                "receipt_id": recebimento.id,
                "beneficiary_id": collaborator_id,
                "operation_amount": str(proposta.operation_amount),
                "company_commission": str(proposta.company_commission_amount),
                "receipt_eligible_amount": str(resultado.contexto.base_elegivel),
                "tps": str(proposta.tps_percentage),
                "tax_regime": consultor.tax_regime,
                "monthly_production_before": str(calculo.producao_anterior),
                "strategy_config_version": config.version,
                "beneficiary_policy_id": None if policy is None else policy.id,
                "commission_excluded": False if policy is None else policy.excluded,
            }
            segmentos = [_segmento_json(item) for item in calculo.segmentos]
            saidas = {
                "recognized_production": str(calculo.producao_reconhecida),
                "monthly_production_after": str(calculo.producao_posterior),
                "commission_amount": str(calculo.comissao),
                "segments": segmentos,
            }
            resumo = json.dumps(entradas, sort_keys=True, separators=(",", ":"))
            snapshot = CommissionCalculationSnapshotModel(
                rule_set_id=None,
                rule_id=None,
                strategy_config_id=config.id,
                proposal_id=proposta.id,
                receipt_id=recebimento.id,
                beneficiary_id=collaborator_id,
                strategy=ESTRATEGIA,
                competence_date=recebimento.business_date,
                inputs=entradas,
                outputs=saidas,
                input_hash=hashlib.sha256(resumo.encode()).hexdigest(),
            )
            self._session.add(snapshot)
            await self._session.flush()
            lancamento = CommissionEntryModel(
                snapshot_id=snapshot.id,
                proposal_id=proposta.id,
                receipt_id=recebimento.id,
                beneficiary_id=collaborator_id,
                entry_type="CREDIT",
                amount=calculo.comissao,
                competence_date=recebimento.business_date,
                description=f"Comissão do Consultor Escalonado — regra {config.version}",
            )
            self._session.add(lancamento)
            await self._session.flush()
            criadas.append(lancamento.id)
            self._saida.registrar(
                event_type="commission.entry_created.v1",
                aggregate_type="commission_entry",
                aggregate_id=str(lancamento.id),
                correlation_id=correlation_id,
                payload={
                    "strategy": ESTRATEGIA,
                    "proposal_id": proposta.id,
                    "receipt_id": recebimento.id,
                    "beneficiary_id": collaborator_id,
                    "amount": str(calculo.comissao),
                    "strategy_config_version": config.version,
                    "segments": segmentos,
                },
            )
        return criadas

    async def producao_acumulada_no_mes(self, collaborator_id: int, data: date) -> Decimal:
        """Produção já reconhecida no mês de `data`, na ordem real de reconhecimento.

        Existe para a prévia de comissão do cadastro da proposta: no escalonado,
        o percentual depende de onde a produção acumulada já chegou. Reusa a
        mesma simulação do cálculo efetivo — duplicar a soma aqui seria assinar
        um segundo motor que diverge do primeiro no primeiro ajuste de regra.
        """
        resultados = await self._simular_mes(collaborator_id, data.year, data.month)
        if not resultados:
            return Decimal("0")
        return resultados[-1].calculo.producao_posterior

    async def _simular_mes(self, collaborator_id: int, ano: int, mes: int) -> list[_Resultado]:
        inicio, fim = _limites_mes(ano, mes)
        linhas = (
            await self._session.execute(
                select(ReceiptModel, ProposalModel)
                .join(ProposalModel, ProposalModel.id == ReceiptModel.proposal_id)
                .where(
                    ProposalModel.consultant_id == collaborator_id,
                    ReceiptModel.status == "APPROVED",
                    ReceiptModel.business_date <= fim,
                )
                .order_by(
                    ReceiptModel.business_date,
                    func.coalesce(ReceiptModel.payment_datetime, ReceiptModel.created_at),
                    ReceiptModel.id,
                )
            )
        ).all()
        if not linhas:
            return []
        ids = [recebimento.id for recebimento, _ in linhas]
        linhas_de_estorno = (
            await self._session.execute(
                select(
                    ReceiptReversalModel.receipt_id,
                    func.sum(ReceiptReversalModel.amount),
                )
                .where(ReceiptReversalModel.receipt_id.in_(ids))
                .group_by(ReceiptReversalModel.receipt_id)
            )
        ).all()
        estornos: dict[int, Decimal] = {
            receipt_id: Decimal(total) for receipt_id, total in linhas_de_estorno
        }
        papeis = list(
            (
                await self._session.scalars(
                    select(CollaboratorRoleModel).where(
                        CollaboratorRoleModel.collaborator_id == collaborator_id,
                        CollaboratorRoleModel.role == PAPEL,
                    )
                )
            ).all()
        )
        saldos: dict[int, Decimal] = {}
        contextos: list[_Contexto] = []
        for recebimento, proposta in linhas:
            saldo = saldos.setdefault(proposta.id, proposta.company_commission_amount)
            liquido = max(
                recebimento.amount - Decimal(estornos.get(recebimento.id) or 0), Decimal("0")
            )
            elegivel = min(liquido, saldo)
            saldos[proposta.id] = saldo - elegivel
            if (
                recebimento.business_date >= inicio
                and elegivel > 0
                and _papel_vigente(papeis, recebimento.business_date)
            ):
                contextos.append(_Contexto(recebimento, proposta, elegivel))

        acumulada = Decimal("0")
        resultados: list[_Resultado] = []
        cache: dict[date, tuple[CommissionStrategyConfigModel, Any]] = {}
        for contexto in contextos:
            data = contexto.recebimento.business_date
            if data not in cache:
                config = await self._configuracao(data)
                cache[data] = (config, interpretar_configuracao_escalonada(config.config))
            config, (faixas_producao, faixas_tps) = cache[data]
            calculo = calcular_consultor_escalonado(
                valor_operacao=contexto.proposta.operation_amount,
                comissao_empresa_total=contexto.proposta.company_commission_amount,
                valor_recebido_elegivel=contexto.base_elegivel,
                tps=contexto.proposta.tps_percentage,
                producao_anterior=acumulada,
                faixas_producao=faixas_producao,
                faixas_tps=faixas_tps,
            )
            policy = await self._policy(collaborator_id, data)
            if policy is not None and policy.excluded:
                calculo = replace(
                    calculo,
                    comissao=Decimal("0.00"),
                    segmentos=tuple(
                        replace(item, comissao_consultor=Decimal("0.00"))
                        for item in calculo.segmentos
                    ),
                )
            acumulada = calculo.producao_posterior
            resultados.append(_Resultado(contexto, config, calculo))
        return resultados

    async def _policy(
        self, collaborator_id: int, data: date
    ) -> CommissionBeneficiaryPolicyModel | None:
        policy: CommissionBeneficiaryPolicyModel | None = await self._session.scalar(
            select(CommissionBeneficiaryPolicyModel)
            .where(
                CommissionBeneficiaryPolicyModel.collaborator_id == collaborator_id,
                CommissionBeneficiaryPolicyModel.valid_from <= data,
                or_(
                    CommissionBeneficiaryPolicyModel.valid_to.is_(None),
                    CommissionBeneficiaryPolicyModel.valid_to >= data,
                ),
            )
            .order_by(CommissionBeneficiaryPolicyModel.valid_from.desc())
            .limit(1)
        )
        return policy

    async def _configuracao(self, data: date) -> CommissionStrategyConfigModel:
        config = await self._session.scalar(
            select(CommissionStrategyConfigModel)
            .where(
                CommissionStrategyConfigModel.strategy == ESTRATEGIA,
                CommissionStrategyConfigModel.status == "ACTIVE",
                CommissionStrategyConfigModel.valid_from <= data,
                or_(
                    CommissionStrategyConfigModel.valid_to.is_(None),
                    CommissionStrategyConfigModel.valid_to >= data,
                ),
            )
            .order_by(
                CommissionStrategyConfigModel.valid_from.desc(),
                CommissionStrategyConfigModel.id.desc(),
            )
            .limit(1)
        )
        if config is None:
            raise RuntimeError(f"Não há configuração {ESTRATEGIA} ativa em {data.isoformat()}.")
        return config


def _limites_mes(ano: int, mes: int) -> tuple[date, date]:
    return date(ano, mes, 1), date(ano, mes, monthrange(ano, mes)[1])


def _papel_vigente(papeis: list[CollaboratorRoleModel], data: date) -> bool:
    return any(
        papel.valid_from <= data and (papel.valid_to is None or papel.valid_to >= data)
        for papel in papeis
    )


def interpretar_configuracao_escalonada(
    config: dict[str, Any],
) -> tuple[tuple[FaixaProducaoEscalonada, ...], tuple[FaixaTpsEscalonada, ...]]:
    faixas_producao = tuple(
        FaixaProducaoEscalonada(
            minimo=Decimal(str(item["min"])),
            maximo=None if item.get("max") is None else Decimal(str(item["max"])),
            percentuais=tuple(Decimal(str(valor)) for valor in item["percentages"]),
        )
        for item in config["production_ranges"]
    )
    faixas_tps = tuple(
        FaixaTpsEscalonada(
            minimo=Decimal(str(item["min"])),
            maximo=None if item.get("max") is None else Decimal(str(item["max"])),
        )
        for item in config["tps_ranges"]
    )
    return faixas_producao, faixas_tps


def _segmento_json(segmento: Any) -> dict[str, str | None]:
    return {
        "production_range_min": str(segmento.faixa_minimo),
        "production_range_max": (
            None if segmento.faixa_maximo is None else str(segmento.faixa_maximo)
        ),
        "recognized_production": str(segmento.producao),
        "percentage": str(segmento.percentual),
        "company_commission": str(segmento.comissao_empresa),
        "consultant_commission": str(segmento.comissao_consultor),
    }
