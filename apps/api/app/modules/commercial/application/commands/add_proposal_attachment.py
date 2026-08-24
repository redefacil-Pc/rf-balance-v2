"""Caso de uso: anexar comprovante de pagamento à proposta.

Só em rascunho ou devolvida: a partir do envio, o conjunto de anexos é o que o
financeiro analisou e não muda por baixo da decisão.

Ordem deliberada: o arquivo sobe para o storage **antes** do commit dos
metadados. Se o commit falhar, sobra um objeto órfão no bucket — inofensivo e
coletável. A ordem inversa deixaria uma linha apontando para arquivo inexistente,
que é um comprovante que não abre na frente do financeiro.
"""

from __future__ import annotations

import hashlib
import uuid
from contextlib import suppress
from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.application.ports.attachment_storage import AttachmentStorage
from app.modules.commercial.domain.errors import (
    ComprovanteInvalidoError,
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
from app.platform.http.uploads import matches_declared_content_type

MODULO = "commercial"

#: comprovante é PDF ou foto; planilha e executável não comprovam pagamento
TIPOS_ACEITOS: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
TAMANHO_MAXIMO = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class AddProposalAttachment:
    proposal_id: int
    file_name: str
    content_type: str
    conteudo: bytes
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ComprovanteAnexado:
    id: int
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str


class AddProposalAttachmentHandler:
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

    async def execute(self, cmd: AddProposalAttachment) -> ComprovanteAnexado:
        self._validar_arquivo(cmd)

        proposta = await self._propostas.obter(cmd.proposal_id)
        if proposta is None:
            raise PropostaNaoEncontradaError(f"Proposta {cmd.proposal_id} não encontrada.")
        if not proposta.editavel_pelo_cadastrante:
            raise PropostaEmAnaliseError()

        # chave gerada aqui, nunca derivada do nome enviado pelo usuário
        extensao = TIPOS_ACEITOS[cmd.content_type]
        chave = f"proposals/{cmd.proposal_id}/{uuid.uuid4().hex}{extensao}"
        digest = hashlib.sha256(cmd.conteudo).hexdigest()

        await self._storage.guardar(
            chave=chave, conteudo=cmd.conteudo, content_type=cmd.content_type
        )

        try:
            anexo = await self._anexos.adicionar(
                proposal_id=cmd.proposal_id,
                file_name=cmd.file_name.strip()[:255],
                content_type=cmd.content_type,
                size_bytes=len(cmd.conteudo),
                storage_key=chave,
                sha256=digest,
                ator=cmd.ator,
            )

            self._audit.registrar(
                module=MODULO,
                action="proposal.attachment_added",
                actor_user_id=cmd.ator,
                aggregate_type="proposal",
                aggregate_id=str(cmd.proposal_id),
                correlation_id=cmd.correlation_id,
                payload={
                    "attachment_id": anexo.id,
                    "file_name": anexo.file_name,
                    "content_type": anexo.content_type,
                    "size_bytes": anexo.size_bytes,
                    "sha256": digest,
                },
            )
            await self._uow.commit()
        except Exception:
            with suppress(Exception):
                await self._storage.remover(chave)
            raise

        return ComprovanteAnexado(
            id=anexo.id,
            file_name=anexo.file_name,
            content_type=anexo.content_type,
            size_bytes=anexo.size_bytes,
            sha256=digest,
        )

    @staticmethod
    def _validar_arquivo(cmd: AddProposalAttachment) -> None:
        if cmd.content_type not in TIPOS_ACEITOS:
            aceitos = ", ".join(sorted(TIPOS_ACEITOS))
            raise ComprovanteInvalidoError(
                f"Tipo de arquivo não aceito ({cmd.content_type}). Envie {aceitos}."
            )
        if not cmd.conteudo:
            raise ComprovanteInvalidoError("O arquivo enviado está vazio.")
        if len(cmd.conteudo) > TAMANHO_MAXIMO:
            raise ComprovanteInvalidoError(
                f"O arquivo passa de {TAMANHO_MAXIMO // (1024 * 1024)} MB."
            )
        if not matches_declared_content_type(cmd.content_type, cmd.conteudo):
            raise ComprovanteInvalidoError(
                "O conteúdo do arquivo não corresponde ao tipo PDF, JPG ou PNG informado."
            )
