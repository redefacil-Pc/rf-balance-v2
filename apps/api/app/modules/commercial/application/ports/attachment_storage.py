"""Porta de armazenamento dos comprovantes.

O caso de uso fala com esta interface, nunca com boto3: o adapter local usa
MinIO, o de produção usa S3, e o teste unitário usa memória — sem mudar comando.

O download passa pela API, não por URL pré-assinada: o endpoint do MinIO dentro
do compose (`minio:9000`) não é alcançável pelo navegador, e servir pelo backend
mantém o RBAC no único lugar que decide acesso (`proposals:read`).
"""

from __future__ import annotations

from typing import Protocol


class AttachmentStorage(Protocol):
    async def guardar(self, *, chave: str, conteudo: bytes, content_type: str) -> None: ...

    async def ler(self, chave: str) -> bytes: ...

    async def remover(self, chave: str) -> None:
        """Idempotente: remover chave inexistente não é erro."""
        ...
