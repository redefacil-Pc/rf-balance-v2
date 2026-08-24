"""Caso de uso: decisão do financeiro — aprovar ou devolver a proposta.

Aprovação e devolução mudam sempre juntas: são os dois desfechos da mesma
análise, exigem a mesma permissão (`proposals:approve`) e gravam os mesmos
carimbos. Por isso um comando com a decisão explícita, e não dois handlers
gêmeos.

A devolução exige motivo — quem cadastrou precisa saber o que corrigir; o
histórico de idas e vindas fica na auditoria.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.application.ports.receipt_recognizer import ReceiptRecognizer
from app.modules.commercial.domain.errors import (
    AutoAprovacaoDePropostaError,
    PropostaNaoEncontradaError,
)
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.commissions.application.standard_commission_engine import (
    StandardCommissionEngine,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

MODULO = "commercial"


class Decisao(StrEnum):
    APROVAR = "APROVAR"
    DEVOLVER = "DEVOLVER"


@dataclass(frozen=True, slots=True)
class DecideProposal:
    proposal_id: int
    version: int
    decisao: Decisao
    #: obrigatório na devolução; ignorado na aprovação
    motivo: str | None = None
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class PropostaDecidida:
    id: int
    approval_status: str
    rejection_reason: str | None
    version: int


class DecideProposalHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        propostas: SqlProposalRepository,
        recebimentos: ReceiptRecognizer,
        comissoes: StandardCommissionEngine,
        audit: AuditRecorder,
        outbox: SqlOutboxRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._propostas = propostas
        self._recebimentos = recebimentos
        self._comissoes = comissoes
        self._audit = audit
        self._outbox = outbox
        self._clock = clock

    async def execute(self, cmd: DecideProposal) -> PropostaDecidida:
        proposta = await self._propostas.obter_para_atualizacao(cmd.proposal_id)
        if proposta is None:
            raise PropostaNaoEncontradaError(f"Proposta {cmd.proposal_id} não encontrada.")

        if cmd.decisao is Decisao.APROVAR:
            if cmd.ator is not None and await self._recebimentos.foi_declarado_por(
                cmd.proposal_id, cmd.ator
            ):
                raise AutoAprovacaoDePropostaError()
            proposta.aprovar()
            acao = "proposal.approved"
            # aprovar é conferir no extrato o que a Finalização declarou: o
            # dinheiro passa a valer aqui, no mesmo commit, e não numa segunda
            # decisão sobre o mesmo valor
            total = await self._recebimentos.reconhecer(cmd.proposal_id, ator=cmd.ator)
            proposta.registrar_total_recebido(total)
            await self._comissoes.gerar_para_proposta(
                cmd.proposal_id, correlation_id=cmd.correlation_id
            )
            payload: dict[str, object] = {"recebimentos_reconhecidos": str(total)}
        else:
            proposta.rejeitar(cmd.motivo or "")
            acao = "proposal.rejected"
            payload = {"reason": proposta.rejection_reason}

        await self._propostas.salvar(
            proposta,
            versao_do_cliente=cmd.version,
            quando=self._clock.now(),
            ator=cmd.ator,
        )

        self._audit.registrar(
            module=MODULO,
            action=acao,
            actor_user_id=cmd.ator,
            aggregate_type="proposal",
            aggregate_id=str(cmd.proposal_id),
            correlation_id=cmd.correlation_id,
            payload=payload,
        )
        self._outbox.registrar(
            event_type=(
                "commercial.proposal_approved.v1"
                if cmd.decisao is Decisao.APROVAR
                else "commercial.proposal_rejected.v1"
            ),
            aggregate_type="proposal",
            aggregate_id=str(cmd.proposal_id),
            correlation_id=cmd.correlation_id,
            payload=payload,
        )
        await self._uow.commit()

        return PropostaDecidida(
            id=cmd.proposal_id,
            approval_status=proposta.approval_status.value,
            rejection_reason=proposta.rejection_reason,
            version=proposta.version,
        )
