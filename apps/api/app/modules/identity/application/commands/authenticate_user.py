"""Caso de uso: autenticar usuário e abrir sessão.

Um único commit ao final, cobrindo sessão, tentativa de login, atualização de
último acesso e auditoria. Falha em qualquer etapa reverte tudo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.identity.application.ports.login_attempt_repository import (
    LoginAttemptRepository,
)
from app.modules.identity.application.ports.password_hasher import PasswordHasher
from app.modules.identity.application.ports.session_repository import SessionRepository
from app.modules.identity.application.ports.user_repository import UserRepository
from app.modules.identity.domain.errors import InvalidCredentialsError, TooManyAttemptsError
from app.modules.identity.domain.policies.login_throttle_policy import LoginThrottlePolicy
from app.modules.identity.domain.value_objects.email_address import EmailAddress
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security.token_generator import gerar_token, hash_do_token
from app.platform.time.clock import Clock

MODULO = "identity"


@dataclass(frozen=True, slots=True)
class AuthenticateUser:
    email: str
    senha: str
    ip_hash: str | None
    user_agent: str | None
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class SessionCriada:
    token: str
    csrf_token: str
    expira_em_segundos: int
    user_id: int
    full_name: str
    email: str
    roles: list[str]
    permissions: list[str]
    must_change_password: bool


class AuthenticateUserHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        users: UserRepository,
        sessions: SessionRepository,
        attempts: LoginAttemptRepository,
        hasher: PasswordHasher,
        audit: AuditRecorder,
        clock: Clock,
        throttle: LoginThrottlePolicy,
        session_ttl: int,
    ) -> None:
        self._uow = uow
        self._users = users
        self._sessions = sessions
        self._attempts = attempts
        self._hasher = hasher
        self._audit = audit
        self._clock = clock
        self._throttle = throttle
        self._session_ttl = session_ttl

    async def execute(self, cmd: AuthenticateUser) -> SessionCriada:
        agora = self._clock.now()
        try:
            email = EmailAddress.normalizar(cmd.email)
        except ValueError as exc:
            raise InvalidCredentialsError() from exc

        falhas = await self._attempts.contar_falhas(
            email=email.valor,
            ip_hash=cmd.ip_hash,
            desde=agora - timedelta(seconds=self._throttle.janela_em_segundos),
        )
        if self._throttle.bloqueado(falhas):
            await self._registrar_falha(cmd, email.valor, "throttled", agora)
            raise TooManyAttemptsError(self._throttle.espera_em_segundos())

        user = await self._users.buscar_por_email(email)
        # a senha é verificada mesmo sem usuário, para não vazar existência de
        # conta pelo tempo de resposta
        hash_de_referencia = user.password_hash if user else _HASH_DUMMY
        senha_correta = self._hasher.verificar(cmd.senha, hash_de_referencia)

        if user is None or not senha_correta:
            await self._registrar_falha(cmd, email.valor, "invalid_credentials", agora)
            raise InvalidCredentialsError()
        if not user.is_active:
            await self._registrar_falha(cmd, email.valor, "inactive", agora)
            raise InvalidCredentialsError()

        token = gerar_token()
        csrf = gerar_token()
        sessao = await self._sessions.criar(
            user_id=user.id,
            token_hash=hash_do_token(token),
            csrf_token=csrf,
            emitida_em=agora,
            expira_em=agora + timedelta(seconds=self._session_ttl),
            ip_hash=cmd.ip_hash,
            user_agent=(cmd.user_agent or "")[:255] or None,
        )

        await self._users.registrar_acesso(user.id, agora)
        await self._attempts.registrar(
            email=email.valor, ip_hash=cmd.ip_hash, sucesso=True, motivo=None, quando=agora
        )
        self._audit.registrar(
            module=MODULO,
            action="session.opened",
            actor_user_id=user.id,
            actor_label=user.full_name,
            aggregate_type="session",
            aggregate_id=str(sessao.id),
            correlation_id=cmd.correlation_id,
            ip_hash=cmd.ip_hash,
            payload={"roles": sorted(user.roles)},
        )
        await self._uow.commit()

        return SessionCriada(
            token=token,
            csrf_token=csrf,
            expira_em_segundos=self._session_ttl,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email.valor,
            roles=sorted(user.roles),
            permissions=sorted(user.permissions),
            must_change_password=user.must_change_password,
        )

    async def _registrar_falha(
        self, cmd: AuthenticateUser, email: str, motivo: str, agora: datetime
    ) -> None:
        await self._attempts.registrar(
            email=email, ip_hash=cmd.ip_hash, sucesso=False, motivo=motivo, quando=agora
        )
        self._audit.registrar(
            module=MODULO,
            action="session.denied",
            actor_label=email,
            correlation_id=cmd.correlation_id,
            ip_hash=cmd.ip_hash,
            payload={"reason": motivo},
        )
        # a tentativa precisa persistir mesmo com a requisição rejeitada
        await self._uow.commit()


# hash descartável, com o mesmo custo do real, usado quando o e-mail não existe
_HASH_DUMMY = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "c2FsdG9wYWRyYW9uYW9zZWNyZXRv$0000000000000000000000000000000000000000000"
)
