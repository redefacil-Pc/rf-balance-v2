"""Caso de uso: remover comprovante de proposta ainda editável.

Ordem inversa à do upload: commit primeiro, remoção do storage depois. Se a
remoção física falhar, sobra objeto órfão no bucket — inofensivo; o inverso
(arquivo removido e commit falho) ressuscitaria a linha apontando para o nada.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.application.ports.attachment_storage import AttachmentStorage
from app.modules.commercial.domain.errors import (
    ComprovanteNaoEncontradoError,
    PropostaEmAnaliseError,
    PropostaNaoEncontradaError,
)
from app.modules.commercial.infrastructure.repositories.sql_proposal_attachment_repository import (
    SqlProposalAttachmentRepository,
)
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork

MODULO = "commercial"


@dataclass(frozen=True, slots=True)
class RemoveProposalAttachment:
    proposal_id: int
    attachment_id: int
    ator: int | None = None
    correlation_id: str | None = None


class RemoveProposalAttachmentHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        propostas: SqlProposalRepository,
        anexos: SqlProposalAttachmentRepository,
        storage: AttachmentStorage,
        audit: AuditRecorder,
    ) -> None:
        self._uow = uow
        self._propostas = propostas
        self._anexos = anexos
        self._storage = storage
        self._audit = audit

    async def execute(self, cmd: RemoveProposalAttachment) -> None:
        proposta = await self._propostas.obter(cmd.proposal_id)
        if proposta is None:
            raise PropostaNaoEncontradaError(f"Proposta {cmd.proposal_id} não encontrada.")
        if not proposta.editavel_pelo_cadastrante:
            raise PropostaEmAnaliseError()

        anexo = await self._anexos.obter(
            proposal_id=cmd.proposal_id, attachment_id=cmd.attachment_id
        )
        if anexo is None:
            raise ComprovanteNaoEncontradoError(
                f"Comprovante {cmd.attachment_id} não encontrado nesta proposta."
            )

        chave = anexo.storage_key
        await self._anexos.remover(cmd.attachment_id)

        self._audit.registrar(
            module=MODULO,
            action="proposal.attachment_removed",
            actor_user_id=cmd.ator,
            aggregate_type="proposal",
            aggregate_id=str(cmd.proposal_id),
            correlation_id=cmd.correlation_id,
            payload={
                "attachment_id": cmd.attachment_id,
                "file_name": anexo.file_name,
                "sha256": anexo.sha256,
            },
        )
        await self._uow.commit()

        await self._storage.remover(chave)
