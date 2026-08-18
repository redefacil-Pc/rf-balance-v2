from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.modules.commissions.api.dependencies import get_period_manager
from app.modules.commissions.api.schemas.period import (
    CommissionPeriodCloseRequest,
    CommissionPeriodRequest,
    CommissionPeriodResponse,
)
from app.modules.commissions.application.manage_periods import CommissionPeriodManager
from app.modules.commissions.infrastructure.models.commission_models import CommissionPeriodModel
from app.modules.identity.api.dependencies import require_permission
from app.modules.identity.domain.entities.user import User

router = APIRouter(prefix="/api/v1/commission-periods", tags=["commissions"])


def _response(model: CommissionPeriodModel) -> CommissionPeriodResponse:
    return CommissionPeriodResponse.model_validate(model, from_attributes=True)


@router.get("", response_model=list[CommissionPeriodResponse])
async def list_periods(
    _actor: Annotated[User, Depends(require_permission("periods:read"))],
    manager: Annotated[CommissionPeriodManager, Depends(get_period_manager)],
) -> list[CommissionPeriodResponse]:
    return [_response(item) for item in await manager.list()]


@router.post("", response_model=CommissionPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_period(
    body: CommissionPeriodRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("periods:close"))],
    manager: Annotated[CommissionPeriodManager, Depends(get_period_manager)],
) -> CommissionPeriodResponse:
    return _response(
        await manager.create(
            period_start=body.period_start,
            period_end=body.period_end,
            cutoff_at=body.cutoff_at,
            reason=body.reason,
            actor=actor.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )


@router.post("/{period_id}/closure", response_model=CommissionPeriodResponse)
async def close_period(
    period_id: int,
    body: CommissionPeriodCloseRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("periods:close"))],
    manager: Annotated[CommissionPeriodManager, Depends(get_period_manager)],
) -> CommissionPeriodResponse:
    return _response(
        await manager.close(
            period_id=period_id,
            reason=body.reason,
            actor=actor.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
