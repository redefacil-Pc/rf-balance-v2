"""Materializa comissões de liderança e finalização na razão imutável."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commissions.domain.group_commissions import (
    comissao_finalizador,
    comissao_lider_comercial,
    comissao_lider_finalizacao,
    comissao_progressiva,
    dinheiro,
)
from app.modules.commissions.infrastructure.models.commission_models import (
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
from app.modules.teams.infrastructure.models.team_assignment_model import TeamAssignmentModel
from app.platform.bus.outbox_recorder import SqlOutboxRecorder

CENTAVO = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class _Recebimento:
    receipt: ReceiptModel
    proposal: ProposalModel
    eligible: Decimal


class GroupCommissionEngine:
    """Um orquestrador para estratégias que compartilham período e vínculos."""

    def __init__(self, session: AsyncSession, outbox: SqlOutboxRecorder) -> None:
        self._session = session
        self._outbox = outbox

    async def gerar_para_proposta(
        self, proposal_id: int, *, correlation_id: str | None
    ) -> list[int]:
        contextos = [
            item for item in await self._recebimentos_liquidos() if item.proposal.id == proposal_id
        ]
        criados: list[int] = []
        for contexto in contextos:
            criados.extend(await self._lider_comercial(contexto, correlation_id))
            criados.extend(await self._lider_geral(contexto, correlation_id))
            criados.extend(await self._finalizacao(contexto, correlation_id))
            criados.extend(await self._lider_finalizacao(contexto, correlation_id))
        return criados

    async def estornar(self, reversal_id: int, *, correlation_id: str | None) -> list[int]:
        estorno = await self._session.get(ReceiptReversalModel, reversal_id)
        if estorno is None:
            return []
        snapshots = list(
            (
                await self._session.scalars(
                    select(CommissionCalculationSnapshotModel).where(
                        CommissionCalculationSnapshotModel.receipt_id == estorno.receipt_id,
                        CommissionCalculationSnapshotModel.strategy.in_(
                            (
                                "COMMERCIAL_LEADER",
                                "GENERAL_MEI_LEADER",
                                "FINALIZER",
                                "FINALIZATION_LEADER",
                            )
                        ),
                    )
                )
            ).all()
        )
        criados: list[int] = []
        for snapshot in snapshots:
            existente = await self._session.scalar(
                select(CommissionEntryModel.id).where(
                    CommissionEntryModel.reversal_id == reversal_id,
                    CommissionEntryModel.snapshot_id == snapshot.id,
                )
            )
            if existente is not None:
                criados.append(existente)
                continue
            if snapshot.strategy == "COMMERCIAL_LEADER":
                valor = await self._diferenca_lider_comercial(snapshot)
            else:
                valor = await self._diferenca_do_periodo(snapshot)
            if valor >= 0:
                continue
            criados.append(await self._lancar_debito(snapshot, estorno, valor, correlation_id))
        return criados

    async def _lider_comercial(
        self, contexto: _Recebimento, correlation_id: str | None
    ) -> list[int]:
        primeiro = await self._session.scalar(
            select(ReceiptModel)
            .where(
                ReceiptModel.proposal_id == contexto.proposal.id,
                ReceiptModel.status == "APPROVED",
            )
            .order_by(
                ReceiptModel.business_date,
                func.coalesce(ReceiptModel.payment_datetime, ReceiptModel.created_at),
                ReceiptModel.id,
            )
            .limit(1)
        )
        if primeiro is None:
            return []
        vinculo = await self._vinculo(
            contexto.proposal.consultant_id, "COMERCIAL", primeiro.business_date
        )
        if vinculo is None:
            return []
        lider = await self._session.get(CollaboratorModel, vinculo.leader_id)
        if lider is None or not await self._papel(lider.id, "LIDER", primeiro.business_date):
            return []
        config = await self._config("COMMERCIAL_LEADER", contexto.receipt.business_date)
        percentual, valor = comissao_lider_comercial(
            base_recebida=contexto.eligible,
            tps=contexto.proposal.tps_percentage,
            regime=lider.tax_regime,
            configuracao=config.config,
        )
        return await self._credito(
            contexto,
            lider.id,
            config,
            inputs={"first_eligible_receipt_date": primeiro.business_date.isoformat()},
            outputs={"percentage": str(percentual), "commission_amount": str(valor)},
            valor=valor,
            descricao="Comissão de líder comercial",
            correlation_id=correlation_id,
        )

    async def _lider_geral(self, contexto: _Recebimento, correlation_id: str | None) -> list[int]:
        consultor = await self._session.get(CollaboratorModel, contexto.proposal.consultant_id)
        if consultor is None or consultor.tax_regime != "MEI":
            return []
        vinculo = await self._vinculo(consultor.id, "MEI_GERAL", contexto.receipt.business_date)
        if vinculo is None:
            return []
        lider = await self._session.get(CollaboratorModel, vinculo.leader_id)
        if lider is None or not await self._papel(
            lider.id, "LIDER_MEI_GERAL", contexto.receipt.business_date
        ):
            return []
        config = await self._config("GENERAL_MEI_LEADER", contexto.receipt.business_date)
        anterior = await self._base_periodo(
            contexto,
            lambda item: self._pertence_lider_geral(item, lider.id),
            antes=True,
            producao=True,
        )
        posterior = anterior + self._producao(contexto)
        percentual_base = Decimal(str(config.config["base_percentage"]))
        antes, _ = comissao_progressiva(
            anterior, percentual_base=percentual_base, faixas=config.config["tiers"]
        )
        depois, segmentos = comissao_progressiva(
            posterior, percentual_base=percentual_base, faixas=config.config["tiers"]
        )
        valor = dinheiro(depois - antes)
        return await self._credito(
            contexto,
            lider.id,
            config,
            inputs={"period_production_before": str(anterior)},
            outputs={
                "period_production_after": str(posterior),
                "base_percentage": str(percentual_base),
                "commission_amount": str(valor),
                "segments": [
                    {
                        "min": str(item.minimo),
                        "max": str(item.maximo),
                        "base": str(item.base),
                        "percentage": str(item.percentual),
                        "commission": str(item.comissao),
                    }
                    for item in segmentos
                ],
            },
            valor=valor,
            descricao="Comissão de líder MEI geral",
            correlation_id=correlation_id,
        )

    async def _finalizacao(self, contexto: _Recebimento, correlation_id: str | None) -> list[int]:
        finalizer_id = contexto.proposal.finalizer_collaborator_id
        if finalizer_id is None or not await self._papel(
            finalizer_id, "FINALIZACAO", contexto.receipt.business_date
        ):
            return []
        config = await self._config("FINALIZER", contexto.receipt.business_date)
        anterior = await self._base_periodo(
            contexto,
            lambda item: _verdadeiro(item.proposal.finalizer_collaborator_id == finalizer_id),
            antes=True,
        )
        posterior = anterior + contexto.eligible
        valor = dinheiro(
            comissao_finalizador(posterior, config.config)
            - comissao_finalizador(anterior, config.config)
        )
        return await self._credito(
            contexto,
            finalizer_id,
            config,
            inputs={"period_base_before": str(anterior)},
            outputs={"period_base_after": str(posterior), "commission_amount": str(valor)},
            valor=valor,
            descricao="Comissão de finalização",
            correlation_id=correlation_id,
        )

    async def _lider_finalizacao(
        self, contexto: _Recebimento, correlation_id: str | None
    ) -> list[int]:
        finalizer_id = contexto.proposal.finalizer_collaborator_id
        if finalizer_id is None:
            return []
        vinculo = await self._vinculo(finalizer_id, "FINALIZACAO", contexto.receipt.business_date)
        if vinculo is None:
            return []
        lider = await self._session.get(CollaboratorModel, vinculo.leader_id)
        if lider is None or not await self._papel(
            lider.id, "LIDER_FINALIZACAO", contexto.receipt.business_date
        ):
            return []
        config = await self._config("FINALIZATION_LEADER", contexto.receipt.business_date)
        anterior = await self._base_periodo(
            contexto, lambda item: self._pertence_lider_finalizacao(item, lider.id), antes=True
        )
        posterior = anterior + contexto.eligible
        percentual, depois = comissao_lider_finalizacao(
            posterior, regime=lider.tax_regime, configuracao=config.config
        )
        _, antes = comissao_lider_finalizacao(
            anterior, regime=lider.tax_regime, configuracao=config.config
        )
        valor = dinheiro(depois - antes)
        return await self._credito(
            contexto,
            lider.id,
            config,
            inputs={"period_team_base_before": str(anterior)},
            outputs={
                "period_team_base_after": str(posterior),
                "percentage": str(percentual),
                "commission_amount": str(valor),
            },
            valor=valor,
            descricao="Comissão de líder de finalização",
            correlation_id=correlation_id,
        )

    async def _credito(
        self,
        contexto: _Recebimento,
        beneficiary_id: int,
        config: CommissionStrategyConfigModel,
        *,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        valor: Decimal,
        descricao: str,
        correlation_id: str | None,
    ) -> list[int]:
        existente = await self._session.scalar(
            select(CommissionCalculationSnapshotModel.id).where(
                CommissionCalculationSnapshotModel.receipt_id == contexto.receipt.id,
                CommissionCalculationSnapshotModel.beneficiary_id == beneficiary_id,
                CommissionCalculationSnapshotModel.strategy == config.strategy,
            )
        )
        if existente is not None:
            return []
        inicio, fim = periodo_semanal(contexto.receipt.business_date)
        entradas = {
            "proposal_id": contexto.proposal.id,
            "receipt_id": contexto.receipt.id,
            "beneficiary_id": beneficiary_id,
            "receipt_eligible_amount": str(contexto.eligible),
            "recognized_production": str(self._producao(contexto)),
            "tps": str(contexto.proposal.tps_percentage),
            "period_start": inicio.isoformat(),
            "period_end": fim.isoformat(),
            "strategy_config_version": config.version,
            **inputs,
        }
        resumo = json.dumps(entradas, sort_keys=True, separators=(",", ":"))
        snapshot = CommissionCalculationSnapshotModel(
            strategy_config_id=config.id,
            proposal_id=contexto.proposal.id,
            receipt_id=contexto.receipt.id,
            beneficiary_id=beneficiary_id,
            strategy=config.strategy,
            competence_date=contexto.receipt.business_date,
            inputs=entradas,
            outputs=outputs,
            input_hash=hashlib.sha256(resumo.encode()).hexdigest(),
        )
        self._session.add(snapshot)
        await self._session.flush()
        entry = CommissionEntryModel(
            snapshot_id=snapshot.id,
            proposal_id=contexto.proposal.id,
            receipt_id=contexto.receipt.id,
            beneficiary_id=beneficiary_id,
            entry_type="CREDIT",
            amount=valor,
            competence_date=contexto.receipt.business_date,
            description=f"{descricao} — regra {config.version}",
        )
        self._session.add(entry)
        await self._session.flush()
        self._outbox.registrar(
            event_type="commission.entry_created.v1",
            aggregate_type="commission_entry",
            aggregate_id=str(entry.id),
            correlation_id=correlation_id,
            payload={
                "strategy": config.strategy,
                "proposal_id": contexto.proposal.id,
                "receipt_id": contexto.receipt.id,
                "beneficiary_id": beneficiary_id,
                "amount": str(valor),
            },
        )
        return [entry.id]

    async def _recebimentos_liquidos(self) -> list[_Recebimento]:
        linhas = (
            await self._session.execute(
                select(ReceiptModel, ProposalModel)
                .join(ProposalModel, ProposalModel.id == ReceiptModel.proposal_id)
                .where(ReceiptModel.status == "APPROVED", ProposalModel.status != "CANCELLED")
                .order_by(
                    ProposalModel.id,
                    ReceiptModel.business_date,
                    func.coalesce(ReceiptModel.payment_datetime, ReceiptModel.created_at),
                    ReceiptModel.id,
                )
            )
        ).all()
        ids = [receipt.id for receipt, _ in linhas]
        reversoes: dict[int, Decimal] = {}
        if ids:
            reversoes = {
                int(item[0]): Decimal(item[1])
                for item in (
                    await self._session.execute(
                        select(
                            ReceiptReversalModel.receipt_id,
                            func.sum(ReceiptReversalModel.amount),
                        )
                        .where(ReceiptReversalModel.receipt_id.in_(ids))
                        .group_by(ReceiptReversalModel.receipt_id)
                    )
                ).all()
            }
        saldos: dict[int, Decimal] = {}
        retorno: list[_Recebimento] = []
        for receipt, proposal in linhas:
            saldo = saldos.setdefault(proposal.id, proposal.company_commission_amount)
            liquido = max(receipt.amount - reversoes.get(receipt.id, Decimal("0")), Decimal("0"))
            elegivel = min(liquido, saldo)
            saldos[proposal.id] = saldo - elegivel
            if elegivel > 0:
                retorno.append(_Recebimento(receipt, proposal, elegivel))
        return retorno

    async def _base_periodo(
        self,
        atual: _Recebimento,
        pertence: Callable[[_Recebimento], Any],
        *,
        antes: bool,
        producao: bool = False,
    ) -> Decimal:
        inicio, fim = periodo_semanal(atual.receipt.business_date)
        total = Decimal("0")
        for item in await self._recebimentos_liquidos():
            if not inicio <= item.receipt.business_date <= fim:
                continue
            if antes and _ordem(item.receipt) >= _ordem(atual.receipt):
                continue
            resultado = pertence(item)
            if hasattr(resultado, "__await__"):
                resultado = await resultado
            if resultado:
                total += self._producao(item) if producao else item.eligible
        return dinheiro(total)

    async def _pertence_lider_geral(self, item: _Recebimento, leader_id: int) -> bool:
        consultor = await self._session.get(CollaboratorModel, item.proposal.consultant_id)
        if consultor is None or consultor.tax_regime != "MEI":
            return False
        vinculo = await self._vinculo(consultor.id, "MEI_GERAL", item.receipt.business_date)
        return vinculo is not None and vinculo.leader_id == leader_id

    async def _pertence_lider_finalizacao(self, item: _Recebimento, leader_id: int) -> bool:
        if item.proposal.finalizer_collaborator_id is None:
            return False
        vinculo = await self._vinculo(
            item.proposal.finalizer_collaborator_id, "FINALIZACAO", item.receipt.business_date
        )
        return vinculo is not None and vinculo.leader_id == leader_id

    async def _diferenca_do_periodo(self, snapshot: CommissionCalculationSnapshotModel) -> Decimal:
        inicio = date.fromisoformat(str(snapshot.inputs["period_start"]))
        fim = date.fromisoformat(str(snapshot.inputs["period_end"]))
        config = await self._session.get(CommissionStrategyConfigModel, snapshot.strategy_config_id)
        beneficiario = await self._session.get(CollaboratorModel, snapshot.beneficiary_id)
        if config is None or beneficiario is None:
            return Decimal("0")
        base = Decimal("0")
        for item in await self._recebimentos_liquidos():
            if not inicio <= item.receipt.business_date <= fim:
                continue
            if snapshot.strategy == "GENERAL_MEI_LEADER" and await self._pertence_lider_geral(
                item, snapshot.beneficiary_id
            ):
                base += self._producao(item)
            elif (
                snapshot.strategy == "FINALIZER"
                and item.proposal.finalizer_collaborator_id == snapshot.beneficiary_id
            ) or (
                snapshot.strategy == "FINALIZATION_LEADER"
                and await self._pertence_lider_finalizacao(item, snapshot.beneficiary_id)
            ):
                base += item.eligible
        if snapshot.strategy == "GENERAL_MEI_LEADER":
            ideal, _ = comissao_progressiva(
                base,
                percentual_base=Decimal(str(config.config["base_percentage"])),
                faixas=config.config["tiers"],
            )
        elif snapshot.strategy == "FINALIZER":
            ideal = comissao_finalizador(base, config.config)
        else:
            _, ideal = comissao_lider_finalizacao(
                base, regime=beneficiario.tax_regime, configuracao=config.config
            )
        atual = Decimal(
            await self._session.scalar(
                select(func.coalesce(func.sum(CommissionEntryModel.amount), 0))
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .where(
                    CommissionCalculationSnapshotModel.strategy == snapshot.strategy,
                    CommissionEntryModel.beneficiary_id == snapshot.beneficiary_id,
                    CommissionCalculationSnapshotModel.competence_date >= inicio,
                    CommissionCalculationSnapshotModel.competence_date <= fim,
                )
            )
            or 0
        )
        return dinheiro(ideal - atual)

    async def _diferenca_lider_comercial(
        self, snapshot: CommissionCalculationSnapshotModel
    ) -> Decimal:
        beneficiary = await self._session.get(CollaboratorModel, snapshot.beneficiary_id)
        if beneficiary is None:
            return Decimal("0.00")
        contexts = {
            item.receipt.id: item
            for item in await self._recebimentos_liquidos()
            if item.proposal.id == snapshot.proposal_id
        }
        snapshots = list(
            (
                await self._session.scalars(
                    select(CommissionCalculationSnapshotModel).where(
                        CommissionCalculationSnapshotModel.proposal_id == snapshot.proposal_id,
                        CommissionCalculationSnapshotModel.beneficiary_id
                        == snapshot.beneficiary_id,
                        CommissionCalculationSnapshotModel.strategy == "COMMERCIAL_LEADER",
                    )
                )
            ).all()
        )
        ideal = Decimal("0")
        for item in snapshots:
            context = contexts.get(item.receipt_id)
            if context is None:
                continue
            config = await self._session.get(CommissionStrategyConfigModel, item.strategy_config_id)
            if config is None:
                continue
            _, amount = comissao_lider_comercial(
                base_recebida=context.eligible,
                tps=context.proposal.tps_percentage,
                regime=beneficiary.tax_regime,
                configuracao=config.config,
            )
            ideal += amount
        current = Decimal(
            await self._session.scalar(
                select(func.coalesce(func.sum(CommissionEntryModel.amount), 0))
                .join(
                    CommissionCalculationSnapshotModel,
                    CommissionCalculationSnapshotModel.id == CommissionEntryModel.snapshot_id,
                )
                .where(
                    CommissionCalculationSnapshotModel.strategy == "COMMERCIAL_LEADER",
                    CommissionEntryModel.proposal_id == snapshot.proposal_id,
                    CommissionEntryModel.beneficiary_id == snapshot.beneficiary_id,
                )
            )
            or 0
        )
        return dinheiro(ideal - current)

    async def _lancar_debito(
        self,
        snapshot: CommissionCalculationSnapshotModel,
        estorno: ReceiptReversalModel,
        valor: Decimal,
        correlation_id: str | None,
    ) -> int:
        entry = CommissionEntryModel(
            snapshot_id=snapshot.id,
            proposal_id=snapshot.proposal_id,
            receipt_id=snapshot.receipt_id,
            reversal_id=estorno.id,
            beneficiary_id=snapshot.beneficiary_id,
            entry_type="DEBIT",
            amount=valor,
            competence_date=estorno.business_date,
            description=f"Recálculo de {snapshot.strategy} — estorno {estorno.id}",
        )
        self._session.add(entry)
        await self._session.flush()
        self._outbox.registrar(
            event_type="commission.entry_reversed.v1",
            aggregate_type="commission_entry",
            aggregate_id=str(entry.id),
            correlation_id=correlation_id,
            payload={
                "strategy": snapshot.strategy,
                "reversal_id": estorno.id,
                "beneficiary_id": snapshot.beneficiary_id,
                "amount": str(valor),
            },
        )
        return entry.id

    async def _config(self, strategy: str, reference: date) -> CommissionStrategyConfigModel:
        config = await self._session.scalar(
            select(CommissionStrategyConfigModel)
            .where(
                CommissionStrategyConfigModel.strategy == strategy,
                CommissionStrategyConfigModel.status == "ACTIVE",
                CommissionStrategyConfigModel.valid_from <= reference,
                or_(
                    CommissionStrategyConfigModel.valid_to.is_(None),
                    CommissionStrategyConfigModel.valid_to >= reference,
                ),
            )
            .order_by(CommissionStrategyConfigModel.valid_from.desc())
            .limit(1)
        )
        if config is None:
            raise RuntimeError(f"Não há configuração {strategy} ativa em {reference}.")
        return config

    async def _vinculo(
        self, collaborator_id: int, assignment_type: str, reference: date
    ) -> TeamAssignmentModel | None:
        vinculo: TeamAssignmentModel | None = await self._session.scalar(
            select(TeamAssignmentModel).where(
                TeamAssignmentModel.consultant_id == collaborator_id,
                TeamAssignmentModel.assignment_type == assignment_type,
                TeamAssignmentModel.start_date <= reference,
                or_(
                    TeamAssignmentModel.end_date.is_(None),
                    TeamAssignmentModel.end_date >= reference,
                ),
            )
        )
        return vinculo

    async def _papel(self, collaborator_id: int, role: str, reference: date) -> bool:
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
    def _producao(item: _Recebimento) -> Decimal:
        return dinheiro(
            item.proposal.operation_amount * item.eligible / item.proposal.company_commission_amount
        )


def periodo_semanal(reference: date) -> tuple[date, date]:
    dias_desde_sexta = (reference.weekday() - 4) % 7
    inicio = reference - timedelta(days=dias_desde_sexta)
    return inicio, inicio + timedelta(days=6)


def _ordem(receipt: ReceiptModel) -> tuple[date, Any, int]:
    return receipt.business_date, receipt.payment_datetime or receipt.created_at, receipt.id


def _verdadeiro(value: bool) -> bool:
    return value
