"""Rotas de autenticação.

O controller apenas autentica/autoriza, valida DTO, cria o command, chama o
handler e converte o resultado — incluindo os cookies (ADR-0003).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.modules.identity.api import cookies
from app.modules.identity.api.dependencies import (
    CurrentUser,
    Uow,
    get_authenticate_handler,
    get_refresh_handler,
    get_revoke_handler,
)
from app.modules.identity.api.schemas.current_user_response import CurrentUserResponse
from app.modules.identity.api.schemas.login_request import LoginRequest
from app.modules.identity.application.commands.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserHandler,
)
from app.modules.identity.application.commands.refresh_session import (
    RefreshSession,
    RefreshSessionHandler,
)
from app.modules.identity.application.commands.revoke_session import (
    RevokeSession,
    RevokeSessionHandler,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.config.security import SESSION_COOKIE
from app.platform.security.token_generator import hash_de_identificador

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _ip_hash(request: Request) -> str | None:
    """Guarda hash do IP, nunca o IP em claro (LGPD, seção 13.3)."""
    encaminhado = request.headers.get("X-Forwarded-For", "")
    ip = encaminhado.split(",")[0].strip() or (request.client.host if request.client else "")
    return hash_de_identificador(ip) if ip else None


@router.post("/login", response_model=CurrentUserResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    uow: Uow,
    handler: Annotated[AuthenticateUserHandler, Depends(get_authenticate_handler)],
) -> CurrentUserResponse:
    resultado = await handler.execute(
        AuthenticateUser(
            email=body.email,
            senha=body.password,
            ip_hash=_ip_hash(request),
            user_agent=request.headers.get("User-Agent"),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )

    cookies.definir(
        response,
        token=resultado.token,
        csrf_token=resultado.csrf_token,
        settings=request.app.state.settings.security,
    )
    permissions = set(resultado.permissions)
    if "OPERACIONAL" in resultado.roles:
        collaborators = SqlCollaboratorRepository(uow.session)
        collaborator = await collaborators.colaborador_da_conta(resultado.user_id)
        if collaborator is not None and collaborator.is_active:
            functions = await collaborators.papeis_vigentes_em(
                collaborator.id, request.app.state.clock.business_date()
            )
            if any(item.role == "FINALIZACAO" for item in functions):
                permissions.update(("receipts:read", "receipts:write"))

    return CurrentUserResponse(
        id=resultado.user_id,
        email=resultado.email,
        full_name=resultado.full_name,
        roles=resultado.roles,
        permissions=sorted(permissions),
        must_change_password=resultado.must_change_password,
    )


# response_model=None é necessário com `from __future__ import annotations`:
# sem isso o FastAPI trata o retorno como corpo e recusa o 204
@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def refresh(
    request: Request,
    response: Response,
    handler: Annotated[RefreshSessionHandler, Depends(get_refresh_handler)],
) -> None:
    renovada = await handler.execute(
        RefreshSession(
            token=request.cookies.get(SESSION_COOKIE, ""),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    cookies.definir(
        response,
        token=renovada.token,
        csrf_token=renovada.csrf_token,
        settings=request.app.state.settings.security,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    request: Request,
    response: Response,
    handler: Annotated[RevokeSessionHandler, Depends(get_revoke_handler)],
) -> None:
    await handler.execute(
        RevokeSession(
            token=request.cookies.get(SESSION_COOKIE, ""),
            motivo="logout",
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    cookies.limpar(response, settings=request.app.state.settings.security)


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse.de_usuario(user)
