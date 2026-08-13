"""Porta de persistência de sessão."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.identity.domain.entities.session import Session


class SessionRepository(Protocol):
    async def criar(
        self,
        *,
        user_id: int,
        token_hash: str,
        csrf_token: str,
        emitida_em: datetime,
        expira_em: datetime,
        ip_hash: str | None,
        user_agent: str | None,
    ) -> Session: ...

    async def buscar_por_token_hash(self, token_hash: str) -> Session | None: ...

    async def rotacionar(
        self, *, session_id: int, novo_token_hash: str, quando: datetime
    ) -> None: ...

    async def marcar_uso(self, *, session_id: int, quando: datetime) -> None: ...

    async def revogar(self, *, session_id: int, quando: datetime, motivo: str) -> None: ...

    async def revogar_do_usuario(self, *, user_id: int, quando: datetime, motivo: str) -> int: ...
