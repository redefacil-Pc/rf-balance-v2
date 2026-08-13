"""Caso de uso: cancelar proposta (seção 7.4).

Cancelamento é soft-delete com motivo obrigatório e carimbo de quem cancelou: em
cadeia financeira nada é removido fisicamente. O estado é terminal — proposta
cancelada não volta; o caminho de correção é cadastrar a proposta certa.

Proposta com recebimento confirmado não é cancelada por aqui: o dinheiro já
entrou e a baixa correta é estorno em `receivables` (F3). Enquanto `receipts` não
existe, o guarda é o valor já recebido consolidado na própria proposta.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.application.ports.period_gate import PeriodGate
from app.modules.commercial.domain.errors import (
    PropostaComRecebimentoError,
    PropostaNaoEncontradaError,
)
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

MODULO = "commercial"


@dataclass(frozen=True, slots=True)
class CancelProposal:
    proposal_id: int
    version: int
    motivo: str
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class PropostaCancelada:
    id: int
    status: str
    version: int


class CancelProposalHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        propostas: SqlProposalRepository,
        periodos: PeriodGate,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._propostas = propostas
        self._periodos = periodos
        self._audit = audit
        self._clock = clock

    async def execute(self, cmd: CancelProposal) -> PropostaCancelada:
        proposta = await self._propostas.obter_para_atualizacao(cmd.proposal_id)
        if proposta is None:
            raise PropostaNaoEncontradaError(f"Proposta {cmd.proposal_id} não encontrada.")

        await self._periodos.garantir_aberto(proposta.business_date)

        if not proposta.paid_amount.zerado:
            raise PropostaComRecebimentoError(
                "A proposta tem recebimento consolidado. Estorne o recebimento antes de cancelar."
            )

        proposta.cancelar()
        await self._propostas.salvar(
            proposta,
            versao_do_cliente=cmd.version,
            quando=self._clock.now(),
            ator=cmd.ator,
            motivo_do_cancelamento=cmd.motivo.strip(),
        )

        self._audit.registrar(
            module=MODULO,
            action="proposal.cancelled",
            actor_user_id=cmd.ator,
            aggregate_type="proposal",
            aggregate_id=str(cmd.proposal_id),
            correlation_id=cmd.correlation_id,
            payload={"reason": cmd.motivo.strip()},
        )
        await self._uow.commit()

        return PropostaCancelada(
            id=cmd.proposal_id, status=proposta.status.value, version=proposta.version
        )
