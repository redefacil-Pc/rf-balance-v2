from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.commercial.api.dependencies import Escopo
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User
from app.modules.reporting.api.schemas.dashboard import (
    DashboardRankingResponse,
    DashboardResponse,
    DashboardSummaryResponse,
    DashboardTrendResponse,
)
from app.modules.reporting.application.queries.dashboard import DashboardQuery

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def dashboard(
    period_start: Annotated[date, Query()],
    period_end: Annotated[date, Query()],
    scope: Escopo,
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("dashboard:read"))],
) -> DashboardResponse:
    try:
        result = await DashboardQuery(uow.session).execute(
            period_start=period_start,
            period_end=period_end,
            scope=scope,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return DashboardResponse(
        period_start=result.period_start,
        period_end=result.period_end,
        summary=DashboardSummaryResponse(
            **{
                field: value if isinstance(value, int) else str(value)
                for field, value in asdict(result.summary).items()
            }
        ),
        trend=[
            DashboardTrendResponse(
                business_date=item.business_date,
                proposal_count=item.proposal_count,
                production_amount=str(item.production_amount),
                recognized_revenue=str(item.recognized_revenue),
            )
            for item in result.trend
        ],
        ranking=[
            DashboardRankingResponse(
                collaborator_id=item.collaborator_id,
                collaborator_name=item.collaborator_name,
                proposal_count=item.proposal_count,
                production_amount=str(item.production_amount),
            )
            for item in result.ranking
        ],
    )
