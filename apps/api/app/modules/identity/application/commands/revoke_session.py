"""Caso de uso: encerrar sessão (logout).

Idempotente: logout de sessão já revogada ou inexistente não é erro — o efeito
desejado (não haver sessão) já está garantido.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.identity.application.ports.session_cache import SessionCache
from app.modules.identity.application.ports.session_repository import SessionRepository
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security.token_generator import hash_do_token
from app.platform.time.clock import Clock

MODULO = "identity"


@dataclass(frozen=True, slots=True)
class RevokeSession:
    token: str
    motivo: str
    correlation_id: str | None


class RevokeSessionHandler:
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

    async def execute(self, cmd: RevokeSession) -> None:
        if not cmd.token:
            return

        token_hash = hash_do_token(cmd.token)
        sessao = await self._sessions.buscar_por_token_hash(token_hash)
        await self._cache.invalidar(token_hash)

        if sessao is None:
            return

        await self._sessions.revogar(
            session_id=sessao.id, quando=self._clock.now(), motivo=cmd.motivo
        )
        self._audit.registrar(
            module=MODULO,
            action="session.revoked",
            actor_user_id=sessao.user_id,
            aggregate_type="session",
            aggregate_id=str(sessao.id),
            correlation_id=cmd.correlation_id,
            payload={"reason": cmd.motivo},
        )
        await self._uow.commit()
