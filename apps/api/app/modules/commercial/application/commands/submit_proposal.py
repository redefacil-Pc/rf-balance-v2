"""Caso de uso: enviar a proposta para aprovação do financeiro.

Somente um recebimento declarado, com o comprovante que lhe pertence, satisfaz
o requisito de envio. Um anexo solto da proposta não informa qual valor o
Financeiro deve conferir e, portanto, nunca pode substituí-lo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.application.ports.receipt_recognizer import ReceiptRecognizer
from app.modules.commercial.domain.errors import PropostaNaoEncontradaError
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

MODULO = "commercial"


@dataclass(frozen=True, slots=True)
class SubmitProposal:
    proposal_id: int
    version: int
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class PropostaEnviada:
    id: int
    approval_status: str
    version: int


class SubmitProposalHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        propostas: SqlProposalRepository,
        recebimentos: ReceiptRecognizer,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._propostas = propostas
        self._recebimentos = recebimentos
        self._audit = audit
        self._clock = clock

    async def execute(self, cmd: SubmitProposal) -> PropostaEnviada:
        proposta = await self._propostas.obter_para_atualizacao(cmd.proposal_id)
        if proposta is None:
            raise PropostaNaoEncontradaError(f"Proposta {cmd.proposal_id} não encontrada.")

        recebimentos = await self._recebimentos.contar_declarados(cmd.proposal_id)
        proposta.enviar_para_aprovacao(quantidade_de_recebimentos=recebimentos)

        await self._propostas.salvar(
            proposta,
            versao_do_cliente=cmd.version,
            quando=self._clock.now(),
            ator=cmd.ator,
        )

        self._audit.registrar(
            module=MODULO,
            action="proposal.submitted",
            actor_user_id=cmd.ator,
            aggregate_type="proposal",
            aggregate_id=str(cmd.proposal_id),
            correlation_id=cmd.correlation_id,
            payload={"receipt_proofs": recebimentos},
        )
        await self._uow.commit()

        return PropostaEnviada(
            id=cmd.proposal_id,
            approval_status=proposta.approval_status.value,
            version=proposta.version,
        )
