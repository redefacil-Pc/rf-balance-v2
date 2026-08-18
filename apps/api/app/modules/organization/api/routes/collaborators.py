"""Rotas de colaboradores."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User
from app.modules.organization.api.dependencies import (
    get_activate_collaborator_handler,
    get_add_function_handler,
    get_bank_account_handler,
    get_close_function_handler,
    get_create_collaborator_handler,
    get_deactivate_collaborator_handler,
    get_link_account_handler,
    get_list_collaborators_handler,
    get_list_functions_handler,
    get_update_collaborator_handler,
)
from app.modules.organization.api.schemas.collaborator import (
    ActivateCollaboratorRequest,
    AddFunctionRequest,
    BankAccountRequest,
    BankAccountResponse,
    CloseFunctionRequest,
    CollaboratorDetailResponse,
    CollaboratorPageResponse,
    CollaboratorRequest,
    CollaboratorResponse,
    DeactivateCollaboratorRequest,
    FunctionResponse,
    LinkAccountRequest,
    UpdateCollaboratorRequest,
)
from app.modules.organization.api.schemas.company import SetCatalogStatusRequest
from app.modules.organization.application.commands.create_collaborator import (
    ChavePixSolicitada,
    CreateCollaborator,
    CreateCollaboratorHandler,
    PapelSolicitado,
)
from app.modules.organization.application.commands.deactivate_collaborator import (
    ActivateCollaborator,
    ActivateCollaboratorHandler,
    DeactivateCollaborator,
    DeactivateCollaboratorHandler,
)
from app.modules.organization.application.commands.link_collaborator_account import (
    LinkCollaboratorAccount,
    LinkCollaboratorAccountHandler,
)
from app.modules.organization.application.commands.manage_bank_account import (
    BankAccountHandler,
    SaveBankAccount,
)
from app.modules.organization.application.commands.manage_collaborator_functions import (
    AddCollaboratorFunction,
    AddCollaboratorFunctionHandler,
    CloseCollaboratorFunction,
    CloseCollaboratorFunctionHandler,
)
from app.modules.organization.application.commands.update_collaborator import (
    UpdateCollaborator,
    UpdateCollaboratorHandler,
)
from app.modules.organization.application.queries.list_collaborator_functions import (
    ListCollaboratorFunctions,
    ListCollaboratorFunctionsHandler,
)
from app.modules.organization.application.queries.list_collaborators import (
    ListCollaborators,
    ListCollaboratorsHandler,
)
from app.modules.organization.domain.errors import RecursoNaoEncontradoError
from app.modules.organization.domain.value_objects.papel_de_colaborador import (
    PapelDeColaborador,
)
from app.modules.organization.infrastructure.repositories.sql_bank_account_repository import (
    SqlBankAccountRepository,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    FiltroDeColaboradores,
    SqlCollaboratorRepository,
)
from app.platform.errors.domain_error import PermissionDeniedError
from app.platform.http.pagination import Cursor, normalizar_limite

router = APIRouter(prefix="/api/v1/collaborators", tags=["organization"])

PERMISSAO_DE_PII = "collaborators:read_pii"


@router.post("", response_model=CollaboratorResponse, status_code=status.HTTP_201_CREATED)
async def criar(
    body: CollaboratorRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("collaborators:write"))],
    handler: Annotated[CreateCollaboratorHandler, Depends(get_create_collaborator_handler)],
) -> CollaboratorResponse:
    # vincular conta é a mesma decisão da rota `/account`, e cobra a mesma
    # permissão. Só que aqui é condicional: cadastrar um BKO, que não loga, não
    # deve exigir permissão de usuários.
    if body.user_id is not None and not ator.pode("users:write"):
        raise PermissionDeniedError("Permissão necessária: users:write.")

    resultado = await handler.execute(
        CreateCollaborator(
            company_id=body.company_id,
            unit_id=body.unit_id,
            full_name=body.full_name,
            documento=body.document,
            regime=body.tax_regime,
            papeis=tuple(
                PapelSolicitado(papel=p.role, valid_from=p.valid_from, valid_to=p.valid_to)
                for p in body.roles
            ),
            email=body.email,
            phone=body.phone,
            chave_pix=(
                ChavePixSolicitada(tipo=body.payment_key.key_type, valor=body.payment_key.key)
                if body.payment_key
                else None
            ),
            user_id=body.user_id,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return CollaboratorResponse(
        id=resultado.id,
        full_name=resultado.full_name,
        company_id=body.company_id,
        unit_id=body.unit_id,
        tax_regime=body.tax_regime.value,
        is_active=True,
        roles=resultado.papeis,
        # a criação nunca devolve o documento completo, mesmo com permissão
        document=resultado.documento_mascarado,
        document_type="CPF" if len(resultado.documento_mascarado) <= 14 else "CNPJ",
        user_id=body.user_id,
    )


@router.get("", response_model=CollaboratorPageResponse)
async def listar(
    request: Request,
    ator: Annotated[User, Depends(require_permission("collaborators:read"))],
    handler: Annotated[ListCollaboratorsHandler, Depends(get_list_collaborators_handler)],
    company_id: Annotated[int | None, Query()] = None,
    unit_id: Annotated[int | None, Query()] = None,
    role: Annotated[str | None, Query()] = None,
    tax_regime: Annotated[str | None, Query()] = None,
    only_active: Annotated[bool | None, Query()] = None,
    linked_user_only: Annotated[bool, Query()] = False,
    name: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    cursor: Annotated[str | None, Query()] = None,
) -> CollaboratorPageResponse:
    pagina = await handler.execute(
        ListCollaborators(
            filtro=FiltroDeColaboradores(
                company_id=company_id,
                unit_id=unit_id,
                papel=role,
                regime=tax_regime,
                somente_ativos=only_active,
                busca_por_nome=name,
                somente_com_conta_ativa=linked_user_only,
            ),
            limite=normalizar_limite(limit),
            cursor=Cursor.decodificar(cursor) if cursor else None,
            referencia=request.app.state.clock.business_date(),
            pode_ver_pii=ator.pode(PERMISSAO_DE_PII),
        )
    )
    return CollaboratorPageResponse(
        # `asdict`, não `vars`: os DTOs usam `slots=True` e não têm `__dict__`
        items=[CollaboratorResponse(**asdict(item)) for item in pagina.itens],
        next_cursor=pagina.proximo_cursor,
    )


@router.post("/{collaborator_id}/deactivation", status_code=status.HTTP_200_OK)
async def inativar(
    collaborator_id: int,
    body: DeactivateCollaboratorRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("collaborators:write"))],
    handler: Annotated[DeactivateCollaboratorHandler, Depends(get_deactivate_collaborator_handler)],
) -> dict[str, int]:
    resultado = await handler.execute(
        DeactivateCollaborator(
            collaborator_id=collaborator_id,
            em=body.deactivated_on,
            motivo=body.reason,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return {
        "id": resultado.id,
        "closed_assignments": resultado.vinculos_encerrados,
        "closed_functions": resultado.funcoes_encerradas,
    }


@router.post(
    "/{collaborator_id}/activation",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reativar(
    collaborator_id: int,
    body: ActivateCollaboratorRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("collaborators:write"))],
    handler: Annotated[ActivateCollaboratorHandler, Depends(get_activate_collaborator_handler)],
) -> None:
    await handler.execute(
        ActivateCollaborator(
            collaborator_id=collaborator_id,
            em=body.activated_on,
            motivo=body.reason,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )


@router.get("/{collaborator_id}/details", response_model=CollaboratorDetailResponse)
async def detalhes_de_edicao(
    collaborator_id: int,
    request: Request,
    _ator: Annotated[User, Depends(require_permission("collaborators:write"))],
    uow: Uow,
) -> CollaboratorDetailResponse:
    repositorio = SqlCollaboratorRepository(uow.session)
    modelo = await repositorio.buscar_por_id(collaborator_id)
    if modelo is None:
        raise RecursoNaoEncontradoError("Colaborador não encontrado.")
    chave = await repositorio.chave_vigente(
        collaborator_id, request.app.state.clock.business_date()
    )
    return CollaboratorDetailResponse(
        id=modelo.id,
        email=modelo.email,
        phone=modelo.phone,
        user_id=modelo.user_id,
        payment_key_type=chave.key_type if chave else None,
        payment_key_masked=chave.key_masked if chave else None,
    )


@router.get("/{collaborator_id}/bank-accounts", response_model=list[BankAccountResponse])
async def listar_contas_bancarias(
    collaborator_id: int,
    _ator: Annotated[User, Depends(require_permission("collaborators:read_pii"))],
    uow: Uow,
) -> list[BankAccountResponse]:
    items = await SqlBankAccountRepository(uow.session).list_for_collaborator(collaborator_id)
    return [
        BankAccountResponse(
            id=item.id,
            bank_code=item.bank_code,
            bank_name=item.bank_name,
            branch=item.branch,
            account_masked=item.account_masked,
            account_type=item.account_type,
            is_active=item.is_active,
        )
        for item in items
    ]


@router.post(
    "/{collaborator_id}/bank-accounts",
    response_model=dict[str, int],
    status_code=status.HTTP_201_CREATED,
)
async def criar_conta_bancaria(
    collaborator_id: int,
    body: BankAccountRequest,
    request: Request,
    ator: Annotated[
        User, Depends(require_permission("collaborators:write", "collaborators:read_pii"))
    ],
    handler: Annotated[BankAccountHandler, Depends(get_bank_account_handler)],
) -> dict[str, int]:
    account_id = await handler.save(
        SaveBankAccount(
            collaborator_id=collaborator_id,
            account_id=None,
            bank_code=body.bank_code,
            bank_name=body.bank_name,
            branch=body.branch,
            account_number=body.account_number,
            account_type=body.account_type,
            actor=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return {"id": account_id}


@router.put(
    "/{collaborator_id}/bank-accounts/{account_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def alterar_conta_bancaria(
    collaborator_id: int,
    account_id: int,
    body: BankAccountRequest,
    request: Request,
    ator: Annotated[
        User, Depends(require_permission("collaborators:write", "collaborators:read_pii"))
    ],
    handler: Annotated[BankAccountHandler, Depends(get_bank_account_handler)],
) -> None:
    await handler.save(
        SaveBankAccount(
            collaborator_id=collaborator_id,
            account_id=account_id,
            bank_code=body.bank_code,
            bank_name=body.bank_name,
            branch=body.branch,
            account_number=body.account_number,
            account_type=body.account_type,
            actor=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )


@router.put(
    "/{collaborator_id}/bank-accounts/{account_id}/status",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def situacao_conta_bancaria(
    collaborator_id: int,
    account_id: int,
    body: SetCatalogStatusRequest,
    request: Request,
    ator: Annotated[
        User, Depends(require_permission("collaborators:write", "collaborators:read_pii"))
    ],
    handler: Annotated[BankAccountHandler, Depends(get_bank_account_handler)],
) -> None:
    await handler.set_status(
        collaborator_id=collaborator_id,
        account_id=account_id,
        active=body.is_active,
        actor=ator.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.put("/{collaborator_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def alterar(
    collaborator_id: int,
    body: UpdateCollaboratorRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("collaborators:write"))],
    handler: Annotated[UpdateCollaboratorHandler, Depends(get_update_collaborator_handler)],
) -> None:
    await handler.execute(
        UpdateCollaborator(
            collaborator_id=collaborator_id,
            company_id=body.company_id,
            unit_id=body.unit_id,
            full_name=body.full_name,
            tax_regime=body.tax_regime,
            email=body.email,
            phone=body.phone,
            chave_pix=(
                ChavePixSolicitada(tipo=body.payment_key.key_type, valor=body.payment_key.key)
                if body.payment_key
                else None
            ),
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            consultant_modality=(
                PapelDeColaborador(body.consultant_modality) if body.consultant_modality else None
            ),
            modality_valid_from=body.modality_valid_from,
            modality_reason=body.modality_reason,
        )
    )


@router.put(
    "/{collaborator_id}/account",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def vincular_conta(
    collaborator_id: int,
    body: LinkAccountRequest,
    request: Request,
    # exige os dois lados: mexer aqui muda o que a pessoa enxerga do sistema
    ator: Annotated[User, Depends(require_permission("collaborators:write", "users:write"))],
    handler: Annotated[LinkCollaboratorAccountHandler, Depends(get_link_account_handler)],
) -> None:
    """Liga a conta de acesso ao colaborador — ou desliga, com `user_id` nulo.

    É esse vínculo que define o escopo de "meus resultados"; por isso a operação
    pede permissão de cadastro **e** de usuários.
    """
    await handler.execute(
        LinkCollaboratorAccount(
            collaborator_id=collaborator_id,
            user_id=body.user_id,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )


@router.get("/{collaborator_id}/functions", response_model=list[FunctionResponse])
async def listar_funcoes(
    collaborator_id: int,
    request: Request,
    ator: Annotated[User, Depends(require_permission("collaborators:read"))],
    handler: Annotated[ListCollaboratorFunctionsHandler, Depends(get_list_functions_handler)],
) -> list[FunctionResponse]:
    """Funções vigentes e encerradas, nessa ordem."""
    funcoes = await handler.execute(
        ListCollaboratorFunctions(
            collaborator_id=collaborator_id,
            referencia=request.app.state.clock.business_date(),
        )
    )
    return [FunctionResponse(**asdict(funcao)) for funcao in funcoes]


@router.post(
    "/{collaborator_id}/functions",
    response_model=FunctionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def abrir_funcao(
    collaborator_id: int,
    body: AddFunctionRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("collaborators:write"))],
    handler: Annotated[AddCollaboratorFunctionHandler, Depends(get_add_function_handler)],
) -> FunctionResponse:
    """Abre uma função. Acumular funções diferentes é legítimo; a mesma função
    não pode se sobrepor a si mesma."""
    criada = await handler.execute(
        AddCollaboratorFunction(
            collaborator_id=collaborator_id,
            funcao=body.function,
            valid_from=body.valid_from,
            valid_to=body.valid_to,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return FunctionResponse(**asdict(criada), current=criada.valid_to is None)


@router.put("/{collaborator_id}/functions/{function_id}/closure", response_model=FunctionResponse)
async def encerrar_funcao(
    collaborator_id: int,
    function_id: int,
    body: CloseFunctionRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("collaborators:write"))],
    handler: Annotated[CloseCollaboratorFunctionHandler, Depends(get_close_function_handler)],
) -> FunctionResponse:
    """Encerra a vigência. A linha permanece: é ela que responde qual era a
    função na data de uma proposta antiga."""
    encerrada = await handler.execute(
        CloseCollaboratorFunction(
            collaborator_id=collaborator_id,
            function_id=function_id,
            valid_to=body.valid_to,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return FunctionResponse(**asdict(encerrada), current=False)
