from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.modules.commissions.api.dependencies import get_strategy_config_manager
from app.modules.commissions.api.schemas.commission_rules import (
    ActivateCommissionRuleSetRequest,
    CreateStrategyConfigRequest,
    StrategyConfigResponse,
)
from app.modules.commissions.application.manage_strategy_configs import (
    CommissionStrategyConfigManager,
)
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionStrategyConfigModel,
)
from app.modules.identity.api.dependencies import require_permission
from app.modules.identity.domain.entities.user import User

router = APIRouter(prefix="/api/v1/commission-strategy-configs", tags=["commissions"])


def response(model: CommissionStrategyConfigModel) -> StrategyConfigResponse:
    return StrategyConfigResponse.model_validate(model, from_attributes=True)


@router.get("", response_model=list[StrategyConfigResponse])
async def list_configs(
    _actor: Annotated[User, Depends(require_permission("commission_rules:read"))],
    manager: Annotated[CommissionStrategyConfigManager, Depends(get_strategy_config_manager)],
) -> list[StrategyConfigResponse]:
    return [response(item) for item in await manager.listar()]


@router.post("", response_model=StrategyConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    body: CreateStrategyConfigRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("commission_rules:write"))],
    manager: Annotated[CommissionStrategyConfigManager, Depends(get_strategy_config_manager)],
) -> StrategyConfigResponse:
    created = await manager.create(
        strategy=body.strategy,
        version=body.version,
        name=body.name,
        valid_from=body.valid_from,
        reason=body.reason,
        config=body.config,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    refreshed = next(item for item in await manager.listar() if item.id == created.id)
    return response(refreshed)


@router.post("/{config_id}/activation", response_model=StrategyConfigResponse)
async def activate_config(
    config_id: int,
    body: ActivateCommissionRuleSetRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("commission_rules:activate"))],
    manager: Annotated[CommissionStrategyConfigManager, Depends(get_strategy_config_manager)],
) -> StrategyConfigResponse:
    activated = await manager.activate(
        config_id=config_id,
        reason=body.reason,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    refreshed = next(item for item in await manager.listar() if item.id == activated.id)
    return response(refreshed)
