from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.modules.commissions.api.dependencies import get_rule_set_manager
from app.modules.commissions.api.schemas.commission_rules import (
    ActivateCommissionRuleSetRequest,
    CommissionBandResponse,
    CommissionRuleSetResponse,
    CreateCommissionRuleSetRequest,
)
from app.modules.commissions.application.manage_rule_sets import CommissionRuleSetManager
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionRuleModel,
    CommissionRuleSetModel,
)
from app.modules.identity.api.dependencies import require_permission
from app.modules.identity.domain.entities.user import User

router = APIRouter(prefix="/api/v1/commission-rule-sets", tags=["commissions"])


def _response(
    conjunto: CommissionRuleSetModel, regras: list[CommissionRuleModel]
) -> CommissionRuleSetResponse:
    return CommissionRuleSetResponse(
        id=conjunto.id,
        strategy=conjunto.strategy,
        version=conjunto.version,
        name=conjunto.name,
        status=conjunto.status,
        valid_from=conjunto.valid_from,
        valid_to=conjunto.valid_to,
        reason=conjunto.reason,
        created_at=conjunto.created_at,
        created_by=conjunto.created_by,
        activated_at=conjunto.activated_at,
        activated_by=conjunto.activated_by,
        rules=[
            CommissionBandResponse(
                id=regra.id,
                tax_regime=regra.tax_regime,
                tps_min=str(regra.tps_min),
                tps_max=None if regra.tps_max is None else str(regra.tps_max),
                percentage=str(regra.percentage),
                sort_order=regra.sort_order,
            )
            for regra in regras
        ],
    )


@router.get("", response_model=list[CommissionRuleSetResponse])
async def listar(
    _actor: Annotated[User, Depends(require_permission("commission_rules:read"))],
    manager: Annotated[CommissionRuleSetManager, Depends(get_rule_set_manager)],
) -> list[CommissionRuleSetResponse]:
    return [_response(conjunto, regras) for conjunto, regras in await manager.listar()]


@router.post("", response_model=CommissionRuleSetResponse, status_code=status.HTTP_201_CREATED)
async def criar(
    body: CreateCommissionRuleSetRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("commission_rules:write"))],
    manager: Annotated[CommissionRuleSetManager, Depends(get_rule_set_manager)],
) -> CommissionRuleSetResponse:
    conjunto = await manager.create(
        version=body.version,
        name=body.name,
        valid_from=body.valid_from,
        reason=body.reason,
        rules=[
            (item.tax_regime, item.tps_min, item.tps_max, item.percentage) for item in body.rules
        ],
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    listados = await manager.listar()
    regras = next(regras for item, regras in listados if item.id == conjunto.id)
    return _response(conjunto, regras)


@router.post("/{rule_set_id}/activation", response_model=CommissionRuleSetResponse)
async def ativar(
    rule_set_id: int,
    body: ActivateCommissionRuleSetRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("commission_rules:activate"))],
    manager: Annotated[CommissionRuleSetManager, Depends(get_rule_set_manager)],
) -> CommissionRuleSetResponse:
    conjunto = await manager.activate(
        rule_set_id=rule_set_id,
        reason=body.reason,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    listados = await manager.listar()
    regras = next(regras for item, regras in listados if item.id == conjunto.id)
    return _response(conjunto, regras)
