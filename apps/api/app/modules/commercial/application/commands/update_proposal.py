"""Caso de uso: alterar campos permitidos da proposta (seção 7.4).

Valor da operação e TPS mudam a comissão da empresa, e por isso só podem ser
alterados com o período aberto: em período fechado a correção é compensatória,
nunca edição do original. O cliente envia a `version` que leu; divergiu, é 409 e
a alteração não acontece — duas telas abertas não se sobrescrevem em silêncio.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.application.ports.period_gate import PeriodGate
from app.modules.commercial.domain.errors import (
    ParticipanteInvalidoError,
    PropostaNaoEncontradaError,
    TpsInvalidoError,
    ValorDaOperacaoInvalidoError,
)
from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock
from app.shared.domain.dinheiro import Dinheiro

MODULO = "commercial"


@dataclass(frozen=True, slots=True)
class UpdateProposal:
    proposal_id: int
    #: versão lida pelo cliente — controle otimista
    version: int
    operation_amount: Decimal
    tps_percentage: Decimal
    bko_collaborator_id: int | None = None
    finalizer_collaborator_id: int | None = None
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class PropostaAtualizada:
    id: int
    status: str
    company_commission_amount: Dinheiro
    outstanding_amount: Dinheiro
    version: int


class UpdateProposalHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        propostas: SqlProposalRepository,
        colaboradores: SqlCollaboratorRepository,
        periodos: PeriodGate,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._propostas = propostas
        self._colaboradores = colaboradores
        self._periodos = periodos
        self._audit = audit
        self._clock = clock

    async def execute(self, cmd: UpdateProposal) -> PropostaAtualizada:
        proposta = await self._propostas.obter_para_atualizacao(cmd.proposal_id)
        if proposta is None:
            raise PropostaNaoEncontradaError(f"Proposta {cmd.proposal_id} não encontrada.")

        await self._periodos.garantir_aberto(proposta.business_date)
        await self._validar_colaboradores(cmd)

        anterior = {
            "operation_amount": str(proposta.operation_amount),
            "tps_percentage": str(proposta.tps),
            "company_commission_amount": str(proposta.company_commission_amount),
            "status": proposta.status.value,
        }

        proposta.bko_collaborator_id = cmd.bko_collaborator_id
        proposta.finalizer_collaborator_id = cmd.finalizer_collaborator_id
        proposta.alterar_operacao(
            operation_amount=self._valor(cmd.operation_amount),
            tps=self._tps(cmd.tps_percentage),
        )

        await self._propostas.salvar(
            proposta,
            versao_do_cliente=cmd.version,
            quando=self._clock.now(),
            ator=cmd.ator,
        )

        self._audit.registrar(
            module=MODULO,
            action="proposal.updated",
            actor_user_id=cmd.ator,
            aggregate_type="proposal",
            aggregate_id=str(cmd.proposal_id),
            correlation_id=cmd.correlation_id,
            payload={
                "antes": anterior,
                "depois": {
                    "operation_amount": str(proposta.operation_amount),
                    "tps_percentage": str(proposta.tps),
                    "company_commission_amount": str(proposta.company_commission_amount),
                    "status": proposta.status.value,
                },
            },
        )
        await self._uow.commit()

        return PropostaAtualizada(
            id=cmd.proposal_id,
            status=proposta.status.value,
            company_commission_amount=proposta.company_commission_amount,
            outstanding_amount=proposta.outstanding_amount,
            version=proposta.version,
        )

    @staticmethod
    def _valor(bruto: Decimal) -> Dinheiro:
        try:
            return Dinheiro.de(bruto)
        except ValueError as exc:
            raise ValorDaOperacaoInvalidoError(str(exc)) from exc

    @staticmethod
    def _tps(bruto: Decimal) -> PercentualTps:
        try:
            return PercentualTps.de(bruto)
        except ValueError as exc:
            raise TpsInvalidoError(str(exc)) from exc

    async def _validar_colaboradores(self, cmd: UpdateProposal) -> None:
        for papel, colaborador_id in (
            ("BKO", cmd.bko_collaborator_id),
            ("finalização", cmd.finalizer_collaborator_id),
        ):
            if colaborador_id is None:
                continue
            if await self._colaboradores.buscar_por_id(colaborador_id) is None:
                raise ParticipanteInvalidoError(f"Colaborador de {papel} não encontrado.")
