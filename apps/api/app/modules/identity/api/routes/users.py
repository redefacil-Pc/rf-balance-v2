"""Rotas de administração de usuários.

Tudo sob `users:read` / `users:write`. Não há rota que devolva hash de senha nem
que recupere a provisória: ela existe no corpo da resposta que a gerou e em
lugar nenhum além disso.

Papéis e situação têm rota própria em vez de entrarem no PUT do cadastro: mudar
acesso é ação distinta de corrigir nome, aparece separada na auditoria e derruba
as sessões em curso.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.modules.identity.api.dependencies import (
    get_create_user_handler,
    get_get_user_handler,
    get_list_users_handler,
    get_reset_password_handler,
    get_set_user_roles_handler,
    get_set_user_status_handler,
    get_update_user_handler,
    require_permission,
)
from app.modules.identity.api.schemas.user import (
    PasswordResetResponse,
    RoleResponse,
    SetRolesRequest,
    SetStatusRequest,
    UpdateUserRequest,
    UserCreatedResponse,
    UserPageResponse,
    UserRequest,
    UserResponse,
)
from app.modules.identity.application.commands.create_user import (
    CreateUser,
    CreateUserHandler,
)
from app.modules.identity.application.commands.manage_user import (
    ResetUserPassword,
    ResetUserPasswordHandler,
    SetUserRoles,
    SetUserRolesHandler,
    SetUserStatus,
    SetUserStatusHandler,
    UpdateUser,
    UpdateUserHandler,
)
from app.modules.identity.application.queries.list_users import (
    GetUser,
    GetUserHandler,
    ListUsers,
    ListUsersHandler,
)
from app.modules.identity.domain.entities.user import User
from app.modules.identity.domain.permission_catalog import NOMES_DOS_PAPEIS, PAPEIS
from app.modules.identity.infrastructure.repositories.sql_user_repository import FiltroDeUsuarios
from app.modules.organization.application.commands.create_collaborator import (
    CreateCollaborator,
    PapelSolicitado,
)
from app.platform.http.pagination import Cursor, normalizar_limite

router = APIRouter(prefix="/api/v1/users", tags=["identity"])


@router.get("/roles", response_model=list[RoleResponse])
async def listar_papeis(
    ator: Annotated[User, Depends(require_permission("users:read"))],
) -> list[RoleResponse]:
    """Papéis disponíveis, direto do catálogo — a tela não os digita à mão."""
    return [
        RoleResponse(code=code, name=NOMES_DOS_PAPEIS[code], permissions=sorted(permissoes))
        for code, permissoes in PAPEIS.items()
    ]


@router.get("", response_model=UserPageResponse)
async def listar(
    ator: Annotated[User, Depends(require_permission("users:read"))],
    handler: Annotated[ListUsersHandler, Depends(get_list_users_handler)],
    role: Annotated[str | None, Query(max_length=30)] = None,
    is_active: Annotated[bool | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    #: `false` lista as contas ainda vinculáveis a um colaborador
    has_collaborator: Annotated[bool | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    cursor: Annotated[str | None, Query()] = None,
) -> UserPageResponse:
    pagina = await handler.execute(
        ListUsers(
            filtro=FiltroDeUsuarios(
                papel=role,
                somente_ativos=is_active,
                busca=search,
                com_colaborador=has_collaborator,
            ),
            limite=normalizar_limite(limit),
            cursor=Cursor.decodificar(cursor) if cursor else None,
        )
    )
    return UserPageResponse(
        items=[UserResponse(**asdict(item)) for item in pagina.itens],
        next_cursor=pagina.proximo_cursor,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def detalhar(
    user_id: int,
    ator: Annotated[User, Depends(require_permission("users:read"))],
    handler: Annotated[GetUserHandler, Depends(get_get_user_handler)],
) -> UserResponse:
    return UserResponse(**asdict(await handler.execute(GetUser(user_id=user_id))))


@router.post("", response_model=UserCreatedResponse, status_code=status.HTTP_201_CREATED)
async def criar(
    body: UserRequest,
    request: Request,
    ator: Annotated[
        User, Depends(require_permission("users:write", "collaborators:write"))
    ],
    handler: Annotated[CreateUserHandler, Depends(get_create_user_handler)],
) -> UserCreatedResponse:
    colaborador = None
    if body.collaborator is not None:
        colaborador = CreateCollaborator(
            company_id=body.collaborator.company_id,
            unit_id=body.collaborator.unit_id,
            full_name=body.full_name,
            documento=body.collaborator.document,
            regime=body.collaborator.tax_regime,
            papeis=(
                PapelSolicitado(
                    papel=body.collaborator.function,
                    valid_from=body.collaborator.valid_from,
                ),
            ),
            email=body.email,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    resultado = await handler.execute(
        CreateUser(
            email=body.email,
            full_name=body.full_name,
            papeis=tuple(body.roles),
            colaborador=colaborador,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return UserCreatedResponse(
        id=resultado.id,
        email=resultado.email,
        full_name=resultado.full_name,
        roles=list(resultado.papeis),
        temporary_password=resultado.senha_provisoria,
        collaborator_id=resultado.colaborador_id,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def alterar(
    user_id: int,
    body: UpdateUserRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("users:write"))],
    handler: Annotated[UpdateUserHandler, Depends(get_update_user_handler)],
    consulta: Annotated[GetUserHandler, Depends(get_get_user_handler)],
) -> UserResponse:
    await handler.execute(
        UpdateUser(
            user_id=user_id,
            email=body.email,
            full_name=body.full_name,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return UserResponse(**asdict(await consulta.execute(GetUser(user_id=user_id))))


@router.put("/{user_id}/roles", response_model=UserResponse)
async def definir_papeis(
    user_id: int,
    body: SetRolesRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("users:write"))],
    handler: Annotated[SetUserRolesHandler, Depends(get_set_user_roles_handler)],
    consulta: Annotated[GetUserHandler, Depends(get_get_user_handler)],
) -> UserResponse:
    await handler.execute(
        SetUserRoles(
            user_id=user_id,
            papeis=tuple(body.roles),
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return UserResponse(**asdict(await consulta.execute(GetUser(user_id=user_id))))


@router.put("/{user_id}/status", response_model=UserResponse)
async def definir_situacao(
    user_id: int,
    body: SetStatusRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("users:write"))],
    handler: Annotated[SetUserStatusHandler, Depends(get_set_user_status_handler)],
    consulta: Annotated[GetUserHandler, Depends(get_get_user_handler)],
) -> UserResponse:
    await handler.execute(
        SetUserStatus(
            user_id=user_id,
            ativo=body.is_active,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return UserResponse(**asdict(await consulta.execute(GetUser(user_id=user_id))))


@router.post("/{user_id}/password-reset", response_model=PasswordResetResponse)
async def redefinir_senha(
    user_id: int,
    request: Request,
    ator: Annotated[User, Depends(require_permission("users:write"))],
    handler: Annotated[ResetUserPasswordHandler, Depends(get_reset_password_handler)],
) -> PasswordResetResponse:
    resultado = await handler.execute(
        ResetUserPassword(
            user_id=user_id,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return PasswordResetResponse(
        id=resultado.id,
        email=resultado.email,
        temporary_password=resultado.senha_provisoria,
    )
