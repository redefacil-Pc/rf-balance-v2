"""Query: o arquivo do comprovante, servido pela API.

Não há URL pré-assinada: o storage não é alcançável pelo navegador no ambiente
local, e servir pelo backend mantém a decisão de acesso no RBAC. O conteúdo é
conferido contra o `sha256` gravado no upload — comprovante é evidência, e
evidência que mudou por baixo precisa estourar, não ser servida como se nada.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.modules.commercial.application.ports.attachment_storage import AttachmentStorage
from app.modules.commercial.application.ports.proposal_scope import EscopoDePropostas
from app.modules.commercial.domain.errors import ComprovanteNaoEncontradoError
from app.modules.commercial.infrastructure.repositories.sql_proposal_attachment_repository import (
    SqlProposalAttachmentRepository,
)
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.platform.errors.domain_error import DomainError


class ComprovanteAdulteradoError(DomainError):
    status = 500
    code = "comprovante-adulterado"
    title = "Comprovante não confere"

    def __init__(self) -> None:
        super().__init__(
            "O arquivo armazenado não corresponde ao hash gravado no envio. "
            "Não será servido; acione a administração."
        )


@dataclass(frozen=True, slots=True)
class GetAttachmentContent:
    proposal_id: int
    attachment_id: int
    #: o arquivo é o dado mais sensível do fluxo — comprovante de pagamento do
    #: cliente. O recorte é verificado antes de qualquer leitura do storage.
    escopo: EscopoDePropostas | None = None


@dataclass(frozen=True, slots=True)
class ConteudoDoComprovante:
    file_name: str
    content_type: str
    conteudo: bytes


class GetAttachmentContentHandler:
    def __init__(
        self,
        *,
        propostas: SqlProposalRepository,
        anexos: SqlProposalAttachmentRepository,
        storage: AttachmentStorage,
    ) -> None:
        self._propostas = propostas
        self._anexos = anexos
        self._storage = storage

    async def execute(self, query: GetAttachmentContent) -> ConteudoDoComprovante:
        # a proposta é conferida primeiro: fora do escopo, o arquivo nem chega a
        # ser procurado no storage
        if await self._propostas.obter_linha(query.proposal_id, escopo=query.escopo) is None:
            raise ComprovanteNaoEncontradoError(
                f"Comprovante {query.attachment_id} não encontrado nesta proposta."
            )

        anexo = await self._anexos.obter(
            proposal_id=query.proposal_id, attachment_id=query.attachment_id
        )
        if anexo is None:
            raise ComprovanteNaoEncontradoError(
                f"Comprovante {query.attachment_id} não encontrado nesta proposta."
            )

        conteudo = await self._storage.ler(anexo.storage_key)
        if hashlib.sha256(conteudo).hexdigest() != anexo.sha256:
            raise ComprovanteAdulteradoError()

        return ConteudoDoComprovante(
            file_name=anexo.file_name,
            content_type=anexo.content_type,
            conteudo=conteudo,
        )
