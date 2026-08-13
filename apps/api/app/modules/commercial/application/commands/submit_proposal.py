"""Caso de uso: enviar a proposta para aprovação do financeiro.

Sem comprovante não envia — a regra mora na entidade; aqui só se conta quantos
anexos existem. O controle otimista por `version` vale como em toda escrita.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.domain.errors import PropostaNaoEncontradaError
from app.modules.commercial.infrastructure.repositories.sql_proposal_attachment_repository import (
    SqlProposalAttachmentRepository,
)
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
        anexos: SqlProposalAttachmentRepository,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._propostas = propostas
        self._anexos = anexos
        self._audit = audit
        self._clock = clock

    async def execute(self, cmd: SubmitProposal) -> PropostaEnviada:
        proposta = await self._propostas.obter_para_atualizacao(cmd.proposal_id)
        if proposta is None:
            raise PropostaNaoEncontradaError(f"Proposta {cmd.proposal_id} não encontrada.")

        comprovantes = await self._anexos.contar(cmd.proposal_id)
        proposta.enviar_para_aprovacao(quantidade_de_comprovantes=comprovantes)

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
            payload={"attachments": comprovantes},
        )
        await self._uow.commit()

        return PropostaEnviada(
            id=cmd.proposal_id,
            approval_status=proposta.approval_status.value,
            version=proposta.version,
        )
