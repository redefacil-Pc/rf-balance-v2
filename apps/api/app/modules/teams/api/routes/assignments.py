"""Rotas de vínculo consultor-líder (seção 7.3)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.teams.api.schemas.assignment import (
    AssignLeaderRequest,
    AssignmentResponse,
    CloseAssignmentRequest,
    LeaderAtDateResponse,
)
from app.modules.teams.application.commands.assign_leader import AssignLeader, AssignLeaderHandler
from app.modules.teams.application.commands.close_assignment import (
    CloseAssignment,
    CloseAssignmentHandler,
)
from app.modules.teams.application.queries.get_leader_at_date import GetLeaderAtDateHandler
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)

router = APIRouter(prefix="/api/v1/assignments", tags=["teams"])


def get_assign_handler(request: Request, uow: Uow) -> AssignLeaderHandler:
    return AssignLeaderHandler(
        uow=uow,
        vinculos=SqlTeamAssignmentRepository(uow.session),
        colaboradores=SqlCollaboratorRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


def get_leader_query_handler(uow: Uow) -> GetLeaderAtDateHandler:
    return GetLeaderAtDateHandler(
        vinculos=SqlTeamAssignmentRepository(uow.session),
        colaboradores=SqlCollaboratorRepository(uow.session),
    )


def get_close_handler(request: Request, uow: Uow) -> CloseAssignmentHandler:
    return CloseAssignmentHandler(
        uow=uow,
        assignments=SqlTeamAssignmentRepository(uow.session),
        audit=SqlAuditRecorder(uow.session, request.app.state.clock),
        clock=request.app.state.clock,
    )


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def vincular(
    body: AssignLeaderRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("teams:write"))],
    handler: Annotated[AssignLeaderHandler, Depends(get_assign_handler)],
) -> AssignmentResponse:
    resultado = await handler.execute(
        AssignLeader(
            consultant_id=body.consultant_id,
            leader_id=body.leader_id,
            assignment_type=body.assignment_type,
            start_date=body.start_date,
            motivo=body.reason,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return AssignmentResponse(
        id=resultado.id,
        consultant_id=resultado.consultant_id,
        leader_id=resultado.leader_id,
        assignment_type=resultado.assignment_type,
        start_date=resultado.start_date,
        previous_closed_on=resultado.vinculo_anterior_encerrado_em,
    )


@router.get("/leader", response_model=LeaderAtDateResponse | None)
async def lider_na_data(
    _ator: Annotated[User, Depends(require_permission("teams:read"))],
    handler: Annotated[GetLeaderAtDateHandler, Depends(get_leader_query_handler)],
    consultant_id: Annotated[int, Query()],
    reference_date: Annotated[date, Query()],
    assignment_type: Annotated[str, Query(pattern="^(COMERCIAL|MEI_GERAL|FINALIZACAO)$")] = (
        "COMERCIAL"
    ),
) -> LeaderAtDateResponse | None:
    """Quem era o líder deste consultor na data informada.

    Consulta de primeira classe: é a mesma que o motor de comissão usará na F4.
    """
    resultado = await handler.execute(
        consultant_id=consultant_id,
        assignment_type=assignment_type,
        referencia=reference_date,
    )
    if resultado is None:
        return None
    # `asdict`, não `vars`: os DTOs usam `slots=True` e não têm `__dict__`
    return LeaderAtDateResponse(**asdict(resultado))


@router.get("/consultant/{consultant_id}", response_model=list[AssignmentResponse])
async def historico_do_consultor(
    consultant_id: int,
    _ator: Annotated[User, Depends(require_permission("teams:read"))],
    uow: Uow,
    assignment_type: Annotated[str | None, Query()] = None,
) -> list[AssignmentResponse]:
    vinculos = await SqlTeamAssignmentRepository(uow.session).do_consultor(
        consultant_id=consultant_id, assignment_type=assignment_type
    )
    return [
        AssignmentResponse(
            id=v.id,
            consultant_id=v.consultant_id,
            leader_id=v.leader_id,
            assignment_type=v.assignment_type,
            start_date=v.start_date,
            end_date=v.end_date,
        )
        for v in vinculos
    ]


@router.put("/{assignment_id}/closure", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def encerrar_vinculo(
    assignment_id: int,
    body: CloseAssignmentRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("teams:write"))],
    handler: Annotated[CloseAssignmentHandler, Depends(get_close_handler)],
) -> None:
    await handler.execute(
        CloseAssignment(
            assignment_id=assignment_id,
            end_date=body.end_date,
            reason=body.reason,
            actor=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
