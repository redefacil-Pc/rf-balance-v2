"""Dependências de autenticação e autorização.

Deny by default: rota protegida declara `Depends(require_permission("x:y"))`.
Nenhuma decisão de autorização acontece no frontend.

A Unit of Work é uma dependência de geração: o FastAPI garante o fechamento da
sessão no fim do request, mesmo quando o handler levanta exceção.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.identity.application.commands.authenticate_user import AuthenticateUserHandler
from app.modules.identity.application.commands.create_user import CreateUserHandler
from app.modules.identity.application.commands.manage_user import (
    ResetUserPasswordHandler,
    SetUserRolesHandler,
    SetUserStatusHandler,
    UpdateUserHandler,
)
from app.modules.identity.application.commands.refresh_session import RefreshSessionHandler
from app.modules.identity.application.commands.revoke_session import RevokeSessionHandler
from app.modules.identity.application.queries.list_users import (
    GetUserHandler,
    ListUsersHandler,
)
from app.modules.identity.application.queries.resolve_session import ResolveSessionHandler
from app.modules.identity.domain.entities.user import User
from app.modules.identity.domain.errors import SessionInvalidError
from app.modules.identity.domain.policies.login_throttle_policy import LoginThrottlePolicy
from app.modules.identity.infrastructure.cache.redis_session_cache import RedisSessionCache
from app.modules.identity.infrastructure.hashing.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.identity.infrastructure.repositories.sql_login_attempt_repository import (
    SqlLoginAttemptRepository,
)
from app.modules.identity.infrastructure.repositories.sql_session_repository import (
    SqlSessionRepository,
)
from app.modules.identity.infrastructure.repositories.sql_user_repository import SqlUserRepository
from app.modules.organization.application.commands.create_collaborator import (
    CreateCollaboratorHandler,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.platform.config.security import SESSION_COOKIE
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.errors.domain_error import PermissionDeniedError


async def get_uow(request: Request) -> AsyncIterator[UnitOfWork]:
    async with UnitOfWork(request.app.state.session_factory) as uow:
        yield uow


Uow = Annotated[UnitOfWork, Depends(get_uow)]


def get_authenticate_handler(request: Request, uow: Uow) -> AuthenticateUserHandler:
    settings = request.app.state.settings
    return AuthenticateUserHandler(
        uow=uow,
        users=SqlUserRepository(uow.session),
        sessions=SqlSessionRepository(uow.session),
        attempts=SqlLoginAttemptRepository(uow.session),
        hasher=Argon2PasswordHasher(),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
        throttle=LoginThrottlePolicy(
            max_tentativas=settings.security.login_max_attempts,
            janela_em_segundos=settings.security.login_attempt_window,
        ),
        session_ttl=settings.security.session_ttl,
    )


def get_refresh_handler(request: Request, uow: Uow) -> RefreshSessionHandler:
    return RefreshSessionHandler(
        uow=uow,
        sessions=SqlSessionRepository(uow.session),
        cache=RedisSessionCache(request.app.state.redis),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_revoke_handler(request: Request, uow: Uow) -> RevokeSessionHandler:
    return RevokeSessionHandler(
        uow=uow,
        sessions=SqlSessionRepository(uow.session),
        cache=RedisSessionCache(request.app.state.redis),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


async def current_user(request: Request, uow: Uow) -> User:
    """Resolve a sessão do cookie.

    O CSRF é validado antes, pela dependência global `csrf.guard` registrada em
    `criar_app` — que cobre também as rotas que não resolvem usuário.
    """
    settings = request.app.state.settings
    handler = ResolveSessionHandler(
        sessions=SqlSessionRepository(uow.session),
        users=SqlUserRepository(uow.session),
        cache=RedisSessionCache(request.app.state.redis),
        clock=request.app.state.clock,
        cache_ttl=settings.security.session_cache_ttl,
    )
    resolvida = await handler.execute(request.cookies.get(SESSION_COOKIE, ""))

    user = resolvida.user
    # Permissão contextual: a função operacional FINALIZACAO é mantida com
    # vigência no colaborador, não como mais um perfil de acesso. Assim somente
    # quem exerce a função hoje recebe a capacidade de lançar recebimentos.
    if "OPERACIONAL" in user.roles:
        collaborators = SqlCollaboratorRepository(uow.session)
        collaborator = await collaborators.colaborador_da_conta(user.id)
        if collaborator is not None and collaborator.is_active:
            functions = await collaborators.papeis_vigentes_em(
                collaborator.id, request.app.state.clock.business_date()
            )
            if any(item.role == "FINALIZACAO" for item in functions):
                user = User(
                    id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    password_hash=user.password_hash,
                    is_active=user.is_active,
                    must_change_password=user.must_change_password,
                    roles=user.roles,
                    permissions=user.permissions | {"receipts:read", "receipts:write"},
                )

    request.state.user_id = user.id
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_permission(*permissoes: str) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Exige todas as permissões informadas."""

    async def verificar(user: CurrentUser) -> User:
        faltando = [p for p in permissoes if not user.pode(p)]
        if faltando:
            raise PermissionDeniedError(f"Permissão necessária: {', '.join(sorted(faltando))}.")
        return user

    return verificar


async def optional_user(request: Request, uow: Uow) -> User | None:
    """Para rotas que mudam de comportamento com e sem sessão."""
    try:
        return await current_user(request, uow)
    except SessionInvalidError:
        return None


# ---------- administração de usuários ----------


def get_create_user_handler(request: Request, uow: Uow) -> CreateUserHandler:
    audit = SqlAuditRecorder(uow.session, request.app.state.clock)
    collaborators = SqlCollaboratorRepository(uow.session)
    return CreateUserHandler(
        uow=uow,
        users=SqlUserRepository(uow.session),
        hasher=Argon2PasswordHasher(),
        audit=audit,
        collaborator_creator=CreateCollaboratorHandler(
            uow=uow,
            colaboradores=collaborators,
            empresas=SqlCompanyRepository(uow.session),
            cipher=request.app.state.pii_cipher,
            audit=audit,
            clock=request.app.state.clock,
        ),
        collaborators=collaborators,
    )


def get_update_user_handler(request: Request, uow: Uow) -> UpdateUserHandler:
    return UpdateUserHandler(
        uow=uow,
        users=SqlUserRepository(uow.session),
        sessions=SqlSessionRepository(uow.session),
        cache=RedisSessionCache(request.app.state.redis),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_set_user_roles_handler(request: Request, uow: Uow) -> SetUserRolesHandler:
    return SetUserRolesHandler(
        uow=uow,
        users=SqlUserRepository(uow.session),
        sessions=SqlSessionRepository(uow.session),
        cache=RedisSessionCache(request.app.state.redis),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_set_user_status_handler(request: Request, uow: Uow) -> SetUserStatusHandler:
    return SetUserStatusHandler(
        uow=uow,
        users=SqlUserRepository(uow.session),
        sessions=SqlSessionRepository(uow.session),
        cache=RedisSessionCache(request.app.state.redis),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_reset_password_handler(request: Request, uow: Uow) -> ResetUserPasswordHandler:
    return ResetUserPasswordHandler(
        uow=uow,
        users=SqlUserRepository(uow.session),
        sessions=SqlSessionRepository(uow.session),
        cache=RedisSessionCache(request.app.state.redis),
        hasher=Argon2PasswordHasher(),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_list_users_handler(uow: Uow) -> ListUsersHandler:
    return ListUsersHandler(users=SqlUserRepository(uow.session))


def get_get_user_handler(uow: Uow) -> GetUserHandler:
    return GetUserHandler(users=SqlUserRepository(uow.session))
