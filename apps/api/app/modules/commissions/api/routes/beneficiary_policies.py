from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.modules.commissions.api.dependencies import get_beneficiary_policy_manager
from app.modules.commissions.api.schemas.beneficiary_policy import (
    BeneficiaryPolicyRequest,
    BeneficiaryPolicyResponse,
)
from app.modules.commissions.application.manage_beneficiary_policies import (
    CommissionBeneficiaryPolicyManager,
)
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionBeneficiaryPolicyModel,
)
from app.modules.identity.api.dependencies import require_permission
from app.modules.identity.domain.entities.user import User

router = APIRouter(prefix="/api/v1/commission-beneficiary-policies", tags=["commissions"])


def _response(model: CommissionBeneficiaryPolicyModel, name: str) -> BeneficiaryPolicyResponse:
    return BeneficiaryPolicyResponse(
        id=model.id,
        collaborator_id=model.collaborator_id,
        collaborator_name=name,
        valid_from=model.valid_from,
        valid_to=model.valid_to,
        excluded=model.excluded,
        override_tps_35_percentage=(
            None
            if model.override_tps_35_percentage is None
            else str(model.override_tps_35_percentage)
        ),
        reason=model.reason,
    )


@router.get("", response_model=list[BeneficiaryPolicyResponse])
async def list_policies(
    _actor: Annotated[User, Depends(require_permission("commission_rules:read"))],
    manager: Annotated[CommissionBeneficiaryPolicyManager, Depends(get_beneficiary_policy_manager)],
) -> list[BeneficiaryPolicyResponse]:
    return [_response(model, name) for model, name in await manager.list()]


@router.post("", response_model=BeneficiaryPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: BeneficiaryPolicyRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("commission_rules:write"))],
    manager: Annotated[CommissionBeneficiaryPolicyManager, Depends(get_beneficiary_policy_manager)],
) -> BeneficiaryPolicyResponse:
    created = await manager.create(
        collaborator_id=body.collaborator_id,
        valid_from=body.valid_from,
        excluded=body.excluded,
        override=body.override_tps_35_percentage,
        reason=body.reason,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    collaborator_name = next(name for model, name in await manager.list() if model.id == created.id)
    return _response(created, collaborator_name)
