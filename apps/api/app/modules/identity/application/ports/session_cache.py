"""Porta de cache da resolução sessão -> usuário.

Cache de dado reconstruível, com TTL curto (ADR-0003). O banco continua sendo a
fonte da verdade; o cache existe para tirar uma consulta do caminho crítico de
todo request autenticado.
"""

from __future__ import annotations

from typing import Protocol

from app.modules.identity.domain.entities.user import User


class SessionCache(Protocol):
    async def obter(self, token_hash: str) -> User | None: ...

    async def guardar(self, token_hash: str, user: User, ttl_segundos: int) -> None: ...

    async def invalidar(self, token_hash: str) -> None: ...
