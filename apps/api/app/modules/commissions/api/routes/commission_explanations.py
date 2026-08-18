from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.commissions.api.schemas.commission_explanation import (
    CommissionCalculationResponse,
    CommissionEntryResponse,
    CommissionExplanationResponse,
)
from app.modules.commissions.application.queries.explain_commissions import (
    CommissionExplanationQuery,
    ExplainedCalculation,
)
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User

router = APIRouter(prefix="/api/v1", tags=["commissions"])


def _response(items: list[ExplainedCalculation]) -> CommissionExplanationResponse:
    return CommissionExplanationResponse(
        items=[
            CommissionCalculationResponse(
                id=item.id,
                proposal_id=item.proposal_id,
                receipt_id=item.receipt_id,
                beneficiary_id=item.beneficiary_id,
                beneficiary_name=item.beneficiary_name,
                strategy=item.strategy,
                rule_version=item.rule_version,
                competence_date=item.competence_date,
                inputs=item.inputs,
                outputs=item.outputs,
                calculated_at=item.calculated_at,
                entries=[
                    CommissionEntryResponse(
                        id=entry.id,
                        entry_type=entry.entry_type,
                        amount=str(entry.amount),
                        competence_date=entry.competence_date,
                        description=entry.description,
                        reversal_id=entry.reversal_id,
                        created_at=entry.created_at,
                    )
                    for entry in item.entries
                ],
                net_amount=str(item.net_amount),
            )
            for item in items
        ],
        total_net_amount=str(sum((item.net_amount for item in items), Decimal("0"))),
    )


@router.get(
    "/receipts/{receipt_id}/commission-calculations",
    response_model=CommissionExplanationResponse,
)
async def explain_receipt(
    receipt_id: int,
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("settlements:read"))],
) -> CommissionExplanationResponse:
    return _response(await CommissionExplanationQuery(uow.session).by_receipt(receipt_id))


@router.get(
    "/proposals/{proposal_id}/commission-calculations",
    response_model=CommissionExplanationResponse,
)
async def explain_proposal(
    proposal_id: int,
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("settlements:read"))],
) -> CommissionExplanationResponse:
    return _response(await CommissionExplanationQuery(uow.session).by_proposal(proposal_id))
