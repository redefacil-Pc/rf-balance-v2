from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.modules.identity.api.dependencies import require_permission
from app.modules.identity.domain.entities.user import User
from app.modules.organization.api.dependencies import get_receiving_account_manager
from app.modules.organization.api.schemas.receiving_account import (
    ReceivingAccountRequest,
    ReceivingAccountResponse,
    ReceivingAccountStatusRequest,
)
from app.modules.organization.application.commands.manage_receiving_accounts import (
    ReceivingAccountManager,
)
from app.modules.organization.infrastructure.models.receiving_account_model import (
    ReceivingAccountModel,
)

router = APIRouter(prefix="/api/v1/receiving-accounts", tags=["organization"])

Manager = Annotated[ReceivingAccountManager, Depends(get_receiving_account_manager)]


def _response(model: ReceivingAccountModel) -> ReceivingAccountResponse:
    return ReceivingAccountResponse.model_validate(model, from_attributes=True)


# quem lança recebimento precisa da lista para escolher a conta; administrar o
# cadastro é ato estrutural e fica com quem já mantém empresas e unidades
@router.get("", response_model=list[ReceivingAccountResponse])
async def list_receiving_accounts(
    _actor: Annotated[User, Depends(require_permission("receipts:read"))],
    manager: Manager,
    only_active: Annotated[bool, Query()] = False,
) -> list[ReceivingAccountResponse]:
    return [_response(item) for item in await manager.list(apenas_ativas=only_active)]


@router.post("", response_model=ReceivingAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_receiving_account(
    body: ReceivingAccountRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("companies:write"))],
    manager: Manager,
) -> ReceivingAccountResponse:
    return _response(
        await manager.create(
            label=body.label,
            display_order=body.display_order,
            actor=actor.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )


@router.put("/{account_id}", response_model=ReceivingAccountResponse)
async def update_receiving_account(
    account_id: int,
    body: ReceivingAccountRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("companies:write"))],
    manager: Manager,
) -> ReceivingAccountResponse:
    return _response(
        await manager.update(
            account_id=account_id,
            label=body.label,
            display_order=body.display_order,
            actor=actor.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )


@router.put("/{account_id}/status", response_model=ReceivingAccountResponse)
async def set_receiving_account_status(
    account_id: int,
    body: ReceivingAccountStatusRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("companies:write"))],
    manager: Manager,
) -> ReceivingAccountResponse:
    return _response(
        await manager.set_status(
            account_id=account_id,
            is_active=body.is_active,
            actor=actor.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
