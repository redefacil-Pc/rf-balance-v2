"""Materializa comissão do consultor padrão na escrita do recebimento."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commissions.application.group_commission_engine import GroupCommissionEngine
from app.modules.commissions.application.scaled_commission_engine import ScaledCommissionEngine
from app.modules.commissions.domain.errors import CommissionRuleConfigurationError
from app.modules.commissions.domain.standard_consultant import (
    FaixaConsultorPadrao,
    calcular_consultor_padrao,
)
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionBeneficiaryPolicyModel,
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
    CommissionPeriodModel,
    CommissionRuleModel,
    CommissionRuleSetModel,
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

ESTRATEGIA = "STANDARD_CONSULTANT"


class StandardCommissionEngine:
    def __init__(self, session: AsyncSession, outbox: SqlOutboxRecorder) -> None:
        self._session = session
        self._outbox = outbox
        self._scaled = ScaledCommissionEngine(session, outbox)
        self._group = GroupCommissionEngine(session, outbox)

    async def gerar_para_proposta(
        self, proposal_id: int, *, correlation_id: str | None
    ) -> list[int]:
        closed_date = await self._session.scalar(
            select(ReceiptModel.business_date)
            .join(
                CommissionPeriodModel,
                (CommissionPeriodModel.period_start <= ReceiptModel.business_date)
                & (CommissionPeriodModel.period_end >= ReceiptModel.business_date),
            )
            .where(
                ReceiptModel.proposal_id == proposal_id,
                ReceiptModel.status == "APPROVED",
                CommissionPeriodModel.status == "CLOSED",
                ~exists(
                    select(CommissionCalculationSnapshotModel.id).where(
                        CommissionCalculationSnapshotModel.receipt_id == ReceiptModel.id,
                        CommissionCalculationSnapshotModel.strategy.in_(
                            (ESTRATEGIA, "SCALED_CONSULTANT")
                        ),
                    )
                ),
            )
            .limit(1)
        )
        if closed_date is not None:
            raise CommissionRuleConfigurationError(
                f"O período de {closed_date.isoformat()} está fechado para comissão."
            )
        escalonadas = await self._scaled.gerar_para_proposta(
            proposal_id, correlation_id=correlation_id
        )
        coletivas = await self._group.gerar_para_proposta(
            proposal_id, correlation_id=correlation_id
        )
        proposta = await self._session.get(ProposalModel, proposal_id)
        if proposta is None:
            return [*escalonadas, *coletivas]
        consultor = await self._session.get(CollaboratorModel, proposta.consultant_id)
        if consultor is None:
            return [*escalonadas, *coletivas]

        recebimentos = list(
            (
                await self._session.scalars(
                    select(ReceiptModel)
                    .where(
                        ReceiptModel.proposal_id == proposal_id,
                        ReceiptModel.status == "APPROVED",
                    )
                    .order_by(
                        ReceiptModel.business_date,
                        ReceiptModel.payment_datetime,
                        ReceiptModel.created_at,
                        ReceiptModel.id,
                    )
                )
            ).all()
        )
        estornos = await self._estornos_por_recebimento([item.id for item in recebimentos])
        consumido = Decimal("0")
        criadas: list[int] = [*escalonadas, *coletivas]
        for recebimento in recebimentos:
            restante = max(proposta.company_commission_amount - consumido, Decimal("0"))
            # Um estorno devolve capacidade ao teto da proposta. Usar o valor
            # original aqui fazia a proposta reabrir corretamente, mas impedia
            # um recebimento substituto de voltar a gerar comissão.
            valor_liquido = max(
                recebimento.amount - estornos.get(recebimento.id, Decimal("0")), Decimal("0")
            )
            base_elegivel = min(valor_liquido, restante)
            consumido += base_elegivel
            if base_elegivel <= 0 or await self._ja_calculado(recebimento.id, consultor.id):
                continue
            if await self._eh_escalonado(consultor.id, recebimento.business_date):
                continue
            # A função CONSULTOR escolhe o motor padrão; MEI/CLT é apenas o regime cadastral.
            conjunto, faixas = await self._configuracao(recebimento.business_date, "MEI")
            policy = await self._policy(consultor.id, recebimento.business_date)
            if policy is not None and (
                policy.excluded
                or (
                    proposta.tps_percentage >= Decimal("35")
                    and policy.override_tps_35_percentage is not None
                )
            ):
                percentage = Decimal("0") if policy.excluded else policy.override_tps_35_percentage
                assert percentage is not None
                faixas = [
                    replace(item, percentual=percentage)
                    if item.contem(proposta.tps_percentage)
                    else item
                    for item in faixas
                ]
            calculo = calcular_consultor_padrao(
                valor_operacao=proposta.operation_amount,
                comissao_empresa=proposta.company_commission_amount,
                tps=proposta.tps_percentage,
                valor_recebido_elegivel=base_elegivel,
                regime="MEI",
                faixas=faixas,
            )
            entradas = {
                "proposal_id": proposta.id,
                "receipt_id": recebimento.id,
                "beneficiary_id": consultor.id,
                "operation_amount": str(proposta.operation_amount),
                "company_commission": str(proposta.company_commission_amount),
                "receipt_eligible_amount": str(base_elegivel),
                "tps": str(proposta.tps_percentage),
                "tax_regime": consultor.tax_regime,
                "rule_set_version": conjunto.version,
                "beneficiary_policy_id": None if policy is None else policy.id,
                "commission_excluded": False if policy is None else policy.excluded,
                "override_tps_35_percentage": (
                    None
                    if policy is None or policy.override_tps_35_percentage is None
                    else str(policy.override_tps_35_percentage)
                ),
            }
            saidas = {
                "percentage": str(calculo.percentual),
                "recognized_production": str(calculo.producao_reconhecida),
                "commission_amount": str(calculo.valor),
            }
            resumo = json.dumps(entradas, sort_keys=True, separators=(",", ":"))
            snapshot = CommissionCalculationSnapshotModel(
                rule_set_id=conjunto.id,
                rule_id=calculo.regra_id,
                proposal_id=proposta.id,
                receipt_id=recebimento.id,
                beneficiary_id=consultor.id,
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
                beneficiary_id=consultor.id,
                entry_type="CREDIT",
                amount=calculo.valor,
                competence_date=recebimento.business_date,
                description=f"Comissão de consultor padrão — regra {conjunto.version}",
            )
            self._session.add(lancamento)
            await self._session.flush()
            criadas.append(lancamento.id)
            self._outbox.registrar(
                event_type="commission.entry_created.v1",
                aggregate_type="commission_entry",
                aggregate_id=str(lancamento.id),
                correlation_id=correlation_id,
                payload={
                    "proposal_id": proposta.id,
                    "receipt_id": recebimento.id,
                    "beneficiary_id": consultor.id,
                    "amount": str(calculo.valor),
                    "rule_set_version": conjunto.version,
                },
            )
        return criadas

    async def estornar(self, reversal_id: int, *, correlation_id: str | None) -> int | None:
        estorno = await self._session.get(ReceiptReversalModel, reversal_id)
        if estorno is None:
            return None
        coletivas = await self._group.estornar(reversal_id, correlation_id=correlation_id)
        if await self._scaled.possui_credito(estorno.receipt_id):
            escalonado = await self._scaled.estornar(reversal_id, correlation_id=correlation_id)
            return escalonado if escalonado is not None else (coletivas[0] if coletivas else None)
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
        )
        if credito is None:
            return coletivas[0] if coletivas else None
        snapshot = await self._session.get(CommissionCalculationSnapshotModel, credito.snapshot_id)
        recebimento = await self._session.get(ReceiptModel, estorno.receipt_id)
        if snapshot is None or recebimento is None:
            return None
        recebimentos = list(
            (
                await self._session.scalars(
                    select(ReceiptModel).where(
                        ReceiptModel.proposal_id == credito.proposal_id,
                        ReceiptModel.status == "APPROVED",
                    )
                )
            ).all()
        )
        estornos = await self._estornos_por_recebimento([item.id for item in recebimentos])
        total_liquido = sum(
            (
                max(item.amount - estornos.get(item.id, Decimal("0")), Decimal("0"))
                for item in recebimentos
            ),
            Decimal("0"),
        )
        proposta = await self._session.get(ProposalModel, credito.proposal_id)
        if proposta is None:
            return coletivas[0] if coletivas else None
        # A parte estornada que estava apenas dentro da tolerância de
        # sobrepagamento não reduz comissão. Da mesma forma, outro recebimento
        # já reconhecido pode manter o teto integralmente coberto.
        base_depois = min(total_liquido, proposta.company_commission_amount)
        base_antes = min(total_liquido + estorno.amount, proposta.company_commission_amount)
        reducao_elegivel = max(base_antes - base_depois, Decimal("0"))
        percentual = Decimal(str(snapshot.outputs["percentage"]))
        valor = -(reducao_elegivel * percentual / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        lancamento = CommissionEntryModel(
            snapshot_id=credito.snapshot_id,
            proposal_id=credito.proposal_id,
            receipt_id=credito.receipt_id,
            reversal_id=estorno.id,
            beneficiary_id=credito.beneficiary_id,
            entry_type="DEBIT",
            amount=valor,
            competence_date=estorno.business_date,
            description=f"Estorno da comissão — recebimento {credito.receipt_id}",
        )
        self._session.add(lancamento)
        await self._session.flush()
        self._outbox.registrar(
            event_type="commission.entry_reversed.v1",
            aggregate_type="commission_entry",
            aggregate_id=str(lancamento.id),
            correlation_id=correlation_id,
            payload={
                "receipt_id": credito.receipt_id,
                "reversal_id": estorno.id,
                "beneficiary_id": credito.beneficiary_id,
                "amount": str(valor),
            },
        )
        return lancamento.id

    async def _estornos_por_recebimento(self, ids: list[int]) -> dict[int, Decimal]:
        if not ids:
            return {}
        linhas = (
            await self._session.execute(
                select(
                    ReceiptReversalModel.receipt_id,
                    func.sum(ReceiptReversalModel.amount),
                )
                .where(ReceiptReversalModel.receipt_id.in_(ids))
                .group_by(ReceiptReversalModel.receipt_id)
            )
        ).all()
        return {int(receipt_id): Decimal(total) for receipt_id, total in linhas}

    async def _ja_calculado(self, receipt_id: int, beneficiary_id: int) -> bool:
        existente = await self._session.scalar(
            select(CommissionCalculationSnapshotModel.id).where(
                CommissionCalculationSnapshotModel.receipt_id == receipt_id,
                CommissionCalculationSnapshotModel.beneficiary_id == beneficiary_id,
                CommissionCalculationSnapshotModel.strategy == ESTRATEGIA,
            )
        )
        return existente is not None

    async def _eh_escalonado(self, collaborator_id: int, data: date) -> bool:
        papel = await self._session.scalar(
            select(CollaboratorRoleModel.id).where(
                CollaboratorRoleModel.collaborator_id == collaborator_id,
                CollaboratorRoleModel.role == "CONSULTOR_MEI_ESCALONADO",
                CollaboratorRoleModel.valid_from <= data,
                or_(
                    CollaboratorRoleModel.valid_to.is_(None), CollaboratorRoleModel.valid_to >= data
                ),
            )
        )
        return papel is not None

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

    async def _configuracao(
        self, data: date, regime: str
    ) -> tuple[CommissionRuleSetModel, list[FaixaConsultorPadrao]]:
        conjunto = await self._session.scalar(
            select(CommissionRuleSetModel)
            .where(
                CommissionRuleSetModel.strategy == ESTRATEGIA,
                CommissionRuleSetModel.status == "ACTIVE",
                CommissionRuleSetModel.valid_from <= data,
                or_(
                    CommissionRuleSetModel.valid_to.is_(None),
                    CommissionRuleSetModel.valid_to >= data,
                ),
            )
            .order_by(CommissionRuleSetModel.valid_from.desc(), CommissionRuleSetModel.id.desc())
            .limit(1)
        )
        if conjunto is None:
            raise RuntimeError(f"Não há regra {ESTRATEGIA} ativa em {data.isoformat()}.")
        regras = list(
            (
                await self._session.scalars(
                    select(CommissionRuleModel)
                    .where(
                        CommissionRuleModel.rule_set_id == conjunto.id,
                        CommissionRuleModel.tax_regime == regime,
                        CommissionRuleModel.role == "CONSULTOR",
                    )
                    .order_by(CommissionRuleModel.sort_order)
                )
            ).all()
        )
        faixas = [
            FaixaConsultorPadrao(
                id=regra.id,
                regime=regra.tax_regime,
                tps_minimo=regra.tps_min,
                tps_maximo=regra.tps_max,
                percentual=regra.percentage,
            )
            for regra in regras
        ]
        return conjunto, faixas
