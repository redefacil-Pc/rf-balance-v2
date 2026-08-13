"""Query: comprovantes de uma proposta, na ordem de envio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.commercial.application.ports.proposal_scope import EscopoDePropostas
from app.modules.commercial.domain.errors import PropostaNaoEncontradaError
from app.modules.commercial.infrastructure.repositories.sql_proposal_attachment_repository import (
    SqlProposalAttachmentRepository,
)
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)


@dataclass(frozen=True, slots=True)
class ComprovanteEmLista:
    id: int
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime
    uploaded_by: int | None


@dataclass(frozen=True, slots=True)
class ListProposalAttachments:
    proposal_id: int
    #: mesmo recorte do detalhe: comprovante de proposta fora do escopo não
    #: existe para quem perguntou
    escopo: EscopoDePropostas | None = None


class ListProposalAttachmentsHandler:
    def __init__(
        self,
        *,
        propostas: SqlProposalRepository,
        anexos: SqlProposalAttachmentRepository,
    ) -> None:
        self._propostas = propostas
        self._anexos = anexos

    async def execute(self, query: ListProposalAttachments) -> list[ComprovanteEmLista]:
        if await self._propostas.obter_linha(query.proposal_id, escopo=query.escopo) is None:
            raise PropostaNaoEncontradaError(f"Proposta {query.proposal_id} não encontrada.")

        return [
            ComprovanteEmLista(
                id=modelo.id,
                file_name=modelo.file_name,
                content_type=modelo.content_type,
                size_bytes=modelo.size_bytes,
                sha256=modelo.sha256,
                uploaded_at=modelo.uploaded_at,
                uploaded_by=modelo.uploaded_by,
            )
            for modelo in await self._anexos.listar(query.proposal_id)
        ]
