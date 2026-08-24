"""Adapter da porta de anexos sobre o object storage S3/MinIO da plataforma.

boto3 é síncrono; cada chamada roda em thread para não travar o event loop da
API enquanto o arquivo sobe ou desce.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.platform.storage.object_storage import chave_com_prefixo


class ObjectAttachmentStorage:
    __slots__ = ("_bucket", "_cliente", "_prefixo")

    def __init__(self, cliente: Any, bucket: str, prefixo: str = "") -> None:
        self._cliente = cliente
        self._bucket = bucket
        self._prefixo = prefixo

    def _chave_fisica(self, chave: str) -> str:
        return chave_com_prefixo(chave, self._prefixo)

    async def guardar(self, *, chave: str, conteudo: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._cliente.put_object,
            Bucket=self._bucket,
            Key=self._chave_fisica(chave),
            Body=conteudo,
            ContentType=content_type,
        )

    async def ler(self, chave: str) -> bytes:
        resposta = await asyncio.to_thread(
            self._cliente.get_object,
            Bucket=self._bucket,
            Key=self._chave_fisica(chave),
        )
        corpo: bytes = await asyncio.to_thread(resposta["Body"].read)
        return corpo

    async def remover(self, chave: str) -> None:
        # delete_object no S3 é idempotente: chave inexistente não levanta
        await asyncio.to_thread(
            self._cliente.delete_object,
            Bucket=self._bucket,
            Key=self._chave_fisica(chave),
        )
