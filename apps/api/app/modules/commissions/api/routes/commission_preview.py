from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.modules.commissions.application.queries.preview_commission import (
    PreviewCommissionHandler,
)
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User

router = APIRouter(prefix="/api/v1/commission-preview", tags=["commissions"])


class CommissionPreviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    consultant_id: int
    business_date: date
    operation_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    tps_percentage: Decimal = Field(ge=0, le=100, max_digits=9, decimal_places=6)


class CommissionPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    company_commission_amount: str
    consultant_commission_amount: str | None
    strategy: str | None
    estimate: bool
    note: str | None


# POST porque é cálculo sobre um corpo, não recurso endereçável; sem efeito
# colateral e sem gravar nada — a prévia não cria proposta nem lançamento
@router.post("", response_model=CommissionPreviewResponse)
async def prever_comissao(
    body: CommissionPreviewRequest,
    _actor: Annotated[User, Depends(require_permission("proposals:write"))],
    uow: Uow,
) -> CommissionPreviewResponse:
    previa = await PreviewCommissionHandler(uow.session).execute(
        consultant_id=body.consultant_id,
        business_date=body.business_date,
        operation_amount=body.operation_amount,
        tps_percentage=body.tps_percentage,
    )
    return CommissionPreviewResponse(
        company_commission_amount=str(previa.company_commission_amount),
        consultant_commission_amount=(
            None
            if previa.consultant_commission_amount is None
            else str(previa.consultant_commission_amount)
        ),
        strategy=previa.strategy,
        estimate=previa.estimate,
        note=previa.note,
    )
