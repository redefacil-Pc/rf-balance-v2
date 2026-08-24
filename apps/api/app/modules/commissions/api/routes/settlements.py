from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.modules.commissions.api.dependencies import get_settlement_manager
from app.modules.commissions.api.schemas.settlement import (
    BkoManualEntryRequest,
    BkoManualEntryResponse,
    FinalizationManualEntryRequest,
    FinalizationManualEntryResponse,
    SettlementAdjustmentRequest,
    SettlementPageResponse,
    SettlementPaymentRequest,
    SettlementPeriodRequest,
    SettlementResponse,
)
from app.modules.commissions.application.manage_settlements import (
    CommissionSettlementManager,
    SettlementView,
)
from app.modules.identity.api.dependencies import require_permission
from app.modules.identity.domain.entities.user import User

router = APIRouter(prefix="/api/v1", tags=["commissions"])


def _response(view: SettlementView) -> SettlementResponse:
    item = view.model
    return SettlementResponse(
        id=item.id,
        beneficiary_id=item.beneficiary_id,
        beneficiary_name=view.beneficiary_name,
        roles=list(view.roles),
        period_start=item.period_start,
        period_end=item.period_end,
        gross_amount=str(item.gross_amount),
        carryover_amount=str(item.carryover_amount),
        bonus_amount=str(item.bonus_amount),
        discount_amount=str(item.discount_amount),
        manual_discount_amount=str(item.manual_discount_amount),
        reversal_discount_amount=str(item.reversal_discount_amount),
        reversal_carryover_amount=str(item.reversal_carryover_amount),
        deferred_amount=str(item.deferred_amount),
        paid_amount=str(item.paid_amount),
        payable_amount=str(item.payable_amount),
        status=item.status,
        payment_date=item.payment_date,
        payment_method=item.payment_method,
        payment_reference=item.payment_reference,
        notes=item.notes,
        created_at=item.created_at,
    )


@router.post(
    "/commission-finalization-entries",
    response_model=FinalizationManualEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_finalization_entry(
    body: FinalizationManualEntryRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("settlements:write"))],
    manager: Annotated[CommissionSettlementManager, Depends(get_settlement_manager)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
) -> FinalizationManualEntryResponse:
    entry = await manager.add_finalization_entry(
        beneficiary_id=body.beneficiary_id,
        amount=body.amount,
        effective_date=body.effective_date,
        description=body.description,
        idempotency_key=idempotency_key,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return FinalizationManualEntryResponse(
        id=entry.id,
        beneficiary_id=entry.beneficiary_id,
        amount=str(entry.amount),
        effective_date=entry.effective_date,
        description=entry.description,
    )


@router.post(
    "/commission-bko-entries",
    response_model=BkoManualEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bko_entry(
    body: BkoManualEntryRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("settlements:write"))],
    manager: Annotated[CommissionSettlementManager, Depends(get_settlement_manager)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
) -> BkoManualEntryResponse:
    entry = await manager.add_bko_entry(
        beneficiary_id=body.beneficiary_id,
        amount=body.amount,
        effective_date=body.effective_date,
        description=body.description,
        idempotency_key=idempotency_key,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return BkoManualEntryResponse(
        id=entry.id,
        beneficiary_id=entry.beneficiary_id,
        amount=str(entry.amount),
        effective_date=entry.effective_date,
        description=entry.description,
    )


@router.get("/commission-settlements", response_model=SettlementPageResponse)
async def list_settlements(
    period_start: Annotated[date, Query()],
    period_end: Annotated[date, Query()],
    _actor: Annotated[User, Depends(require_permission("settlements:read"))],
    manager: Annotated[CommissionSettlementManager, Depends(get_settlement_manager)],
) -> SettlementPageResponse:
    return SettlementPageResponse(
        items=[
            _response(item)
            for item in await manager.list(period_start=period_start, period_end=period_end)
        ]
    )


@router.post("/commission-settlements/generation", response_model=SettlementPageResponse)
async def generate_settlements(
    body: SettlementPeriodRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("settlements:write"))],
    manager: Annotated[CommissionSettlementManager, Depends(get_settlement_manager)],
) -> SettlementPageResponse:
    items = await manager.generate(
        period_start=body.period_start,
        period_end=body.period_end,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return SettlementPageResponse(items=[_response(item) for item in items])


@router.put(
    "/commission-settlements/{settlement_id}/adjustments", response_model=SettlementResponse
)
async def adjust_settlement(
    settlement_id: int,
    body: SettlementAdjustmentRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("settlements:write"))],
    manager: Annotated[CommissionSettlementManager, Depends(get_settlement_manager)],
) -> SettlementResponse:
    return _response(
        await manager.adjust(
            settlement_id=settlement_id,
            bonus_amount=body.bonus_amount,
            discount_amount=body.discount_amount,
            deferred_amount=body.deferred_amount,
            notes=body.notes,
            actor=actor.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )


@router.post("/commission-settlements/{settlement_id}/payments", response_model=SettlementResponse)
async def pay_settlement(
    settlement_id: int,
    body: SettlementPaymentRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("settlements:write"))],
    manager: Annotated[CommissionSettlementManager, Depends(get_settlement_manager)],
) -> SettlementResponse:
    return _response(
        await manager.pay(
            settlement_id=settlement_id,
            amount=body.amount,
            payment_date=body.payment_date,
            payment_method=body.payment_method,
            reference=body.reference,
            actor=actor.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
