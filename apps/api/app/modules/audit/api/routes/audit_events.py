from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.audit.api.schemas.audit_event import (
    AuditEventPageResponse,
    AuditEventResponse,
    AuditOptionsResponse,
)
from app.modules.audit.application.queries.list_audit_events import (
    AuditFilters,
    ListAuditEventsQuery,
)
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User
from app.platform.http.pagination import Cursor, normalizar_limite

router = APIRouter(prefix="/api/v1/audit-events", tags=["audit"])


@router.get("/options", response_model=AuditOptionsResponse)
async def audit_options(
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("audit:read"))],
) -> AuditOptionsResponse:
    modules, actions, aggregate_types = await ListAuditEventsQuery(uow.session).options()
    return AuditOptionsResponse(
        modules=modules,
        actions=actions,
        aggregate_types=aggregate_types,
    )


@router.get("", response_model=AuditEventPageResponse)
async def list_audit_events(
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("audit:read"))],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    module: Annotated[str | None, Query(max_length=40)] = None,
    action: Annotated[str | None, Query(max_length=60)] = None,
    actor: Annotated[str | None, Query(max_length=200)] = None,
    aggregate_type: Annotated[str | None, Query(max_length=40)] = None,
    aggregate_id: Annotated[str | None, Query(max_length=64)] = None,
    correlation_id: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    cursor: Annotated[str | None, Query()] = None,
) -> AuditEventPageResponse:
    page = await ListAuditEventsQuery(uow.session).execute(
        filters=AuditFilters(
            start_date=start_date,
            end_date=end_date,
            module=module,
            action=action,
            actor=actor,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
        ),
        limit=normalizar_limite(limit),
        cursor=Cursor.decodificar(cursor) if cursor else None,
    )
    return AuditEventPageResponse(
        items=[AuditEventResponse(**asdict(item)) for item in page.itens],
        next_cursor=page.proximo_cursor,
    )
