"""Rotas de empresas e unidades."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.modules.identity.api.dependencies import require_permission
from app.modules.identity.domain.entities.user import User
from app.modules.organization.api.dependencies import (
    get_company_repository,
    get_create_company_handler,
    get_create_unit_handler,
)
from app.modules.organization.api.schemas.company import (
    CompanyRequest,
    CompanyResponse,
    UnitRequest,
    UnitResponse,
)
from app.modules.organization.application.commands.create_company import (
    CreateCompany,
    CreateCompanyHandler,
)
from app.modules.organization.application.commands.create_unit import CreateUnit, CreateUnitHandler
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)

router = APIRouter(prefix="/api/v1", tags=["organization"])


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def criar_empresa(
    body: CompanyRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("companies:write"))],
    handler: Annotated[CreateCompanyHandler, Depends(get_create_company_handler)],
) -> CompanyResponse:
    resultado = await handler.execute(
        CreateCompany(
            legal_name=body.legal_name,
            trade_name=body.trade_name,
            documento=body.document,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return CompanyResponse(
        id=resultado.id, legal_name=resultado.legal_name, trade_name=body.trade_name, is_active=True
    )


@router.get("/companies", response_model=list[CompanyResponse])
async def listar_empresas(
    _ator: Annotated[User, Depends(require_permission("collaborators:read"))],
    empresas: Annotated[SqlCompanyRepository, Depends(get_company_repository)],
    only_active: Annotated[bool, Query()] = True,
) -> list[CompanyResponse]:
    return [
        CompanyResponse(
            id=modelo.id,
            legal_name=modelo.legal_name,
            trade_name=modelo.trade_name,
            is_active=modelo.is_active,
        )
        for modelo in await empresas.listar(somente_ativas=only_active)
    ]


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def criar_unidade(
    body: UnitRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("companies:write"))],
    handler: Annotated[CreateUnitHandler, Depends(get_create_unit_handler)],
) -> UnitResponse:
    resultado = await handler.execute(
        CreateUnit(
            company_id=body.company_id,
            code=body.code,
            name=body.name,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return UnitResponse(
        id=resultado.id,
        company_id=resultado.company_id,
        code=resultado.code,
        name=resultado.name,
        is_active=True,
    )


@router.get("/units", response_model=list[UnitResponse])
async def listar_unidades(
    _ator: Annotated[User, Depends(require_permission("collaborators:read"))],
    empresas: Annotated[SqlCompanyRepository, Depends(get_company_repository)],
    company_id: Annotated[int | None, Query()] = None,
    only_active: Annotated[bool, Query()] = True,
) -> list[UnitResponse]:
    return [
        UnitResponse(
            id=modelo.id,
            company_id=modelo.company_id,
            code=modelo.code,
            name=modelo.name,
            is_active=modelo.is_active,
        )
        for modelo in await empresas.listar_unidades(
            company_id=company_id, somente_ativas=only_active
        )
    ]
