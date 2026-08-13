"""Caso de uso: rotacionar o token da sessão (ADR-0003).

Token antigo apresentado depois da rotação indica replay: a sessão é revogada
em vez de renovada.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.identity.application.ports.session_cache import SessionCache
from app.modules.identity.application.ports.session_repository import SessionRepository
from app.modules.identity.domain.errors import SessionInvalidError
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security.token_generator import gerar_token, hash_do_token
from app.platform.time.clock import Clock

MODULO = "identity"


@dataclass(frozen=True, slots=True)
class RefreshSession:
    token: str
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class SessaoRenovada:
    token: str
    csrf_token: str


class RefreshSessionHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        sessions: SessionRepository,
        cache: SessionCache,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._sessions = sessions
        self._cache = cache
        self._audit = audit
        self._clock = clock

    async def execute(self, cmd: RefreshSession) -> SessaoRenovada:
        agora = self._clock.now()
        antigo_hash = hash_do_token(cmd.token)

        sessao = await self._sessions.buscar_por_token_hash(antigo_hash)
        if sessao is None:
            raise SessionInvalidError()

        if not sessao.esta_viva(agora):
            await self._cache.invalidar(antigo_hash)
            raise SessionInvalidError()

        novo_token = gerar_token()
        await self._sessions.rotacionar(
            session_id=sessao.id, novo_token_hash=hash_do_token(novo_token), quando=agora
        )
        await self._cache.invalidar(antigo_hash)
        self._audit.registrar(
            module=MODULO,
            action="session.rotated",
            actor_user_id=sessao.user_id,
            aggregate_type="session",
            aggregate_id=str(sessao.id),
            correlation_id=cmd.correlation_id,
        )
        await self._uow.commit()

        return SessaoRenovada(token=novo_token, csrf_token=sessao.csrf_token)
