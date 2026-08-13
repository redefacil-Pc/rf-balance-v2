"""Caso de uso de leitura: resolver o token do cookie no usuário autenticado.

Roda em todo request autenticado. Tenta o cache primeiro; no miss, consulta o
banco e reabastece. Sessão expirada ou revogada nunca resolve.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.identity.application.ports.session_cache import SessionCache
from app.modules.identity.application.ports.session_repository import SessionRepository
from app.modules.identity.application.ports.user_repository import UserRepository
from app.modules.identity.domain.entities.session import Session
from app.modules.identity.domain.entities.user import User
from app.modules.identity.domain.errors import SessionInvalidError
from app.platform.security.token_generator import hash_do_token
from app.platform.time.clock import Clock


@dataclass(frozen=True, slots=True)
class SessaoResolvida:
    user: User
    sessao: Session | None
    veio_do_cache: bool


class ResolveSessionHandler:
    def __init__(
        self,
        *,
        sessions: SessionRepository,
        users: UserRepository,
        cache: SessionCache,
        clock: Clock,
        cache_ttl: int,
    ) -> None:
        self._sessions = sessions
        self._users = users
        self._cache = cache
        self._clock = clock
        self._cache_ttl = cache_ttl

    async def execute(self, token: str) -> SessaoResolvida:
        if not token:
            raise SessionInvalidError("Sessão ausente.")

        token_hash = hash_do_token(token)

        if em_cache := await self._cache.obter(token_hash):
            return SessaoResolvida(user=em_cache, sessao=None, veio_do_cache=True)

        sessao = await self._sessions.buscar_por_token_hash(token_hash)
        if sessao is None or not sessao.esta_viva(self._clock.now()):
            raise SessionInvalidError()

        user = await self._users.buscar_por_id(sessao.user_id)
        if user is None or not user.is_active:
            raise SessionInvalidError("Usuário inativo.")

        await self._cache.guardar(token_hash, user, self._cache_ttl)
        return SessaoResolvida(user=user, sessao=sessao, veio_do_cache=False)
