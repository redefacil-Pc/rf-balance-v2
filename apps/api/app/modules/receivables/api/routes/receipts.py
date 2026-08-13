from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from app.modules.commercial.infrastructure.storage.object_attachment_storage import (
    ObjectAttachmentStorage,
)
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.receivables.api.dependencies import get_receipt_service
from app.modules.receivables.api.schemas.receipt import (
    ReceiptDecision,
    ReceiptDecisionRequest,
    ReceiptPageResponse,
    ReceiptResponse,
    ReceiptReversalRequest,
    ReceiptWriteResponse,
)
from app.modules.receivables.application.receipt_service import ReceiptResult, ReceiptService
from app.modules.receivables.domain.errors import LancadorDeRecebimentoInvalidoError

router = APIRouter(prefix="/api/v1", tags=["receivables"])


def _write_response(result: ReceiptResult) -> ReceiptWriteResponse:
    return ReceiptWriteResponse(
        id=result.receipt.id,
        proposal_id=result.receipt.proposal_id,
        status=result.receipt.status,
        amount=str(result.receipt.amount),
        proposal_status=result.proposal_status,
        proposal_paid_amount=str(result.proposal_paid_amount),
        proposal_outstanding_amount=str(result.proposal_outstanding_amount),
    )


async def _require_launcher(actor: User, uow: Uow, reference: date) -> None:
    if "FINANCEIRO" in actor.roles:
        return
    if "OPERACIONAL" in actor.roles:
        repo = SqlCollaboratorRepository(uow.session)
        collaborator = await repo.colaborador_da_conta(actor.id)
        if collaborator is not None and collaborator.is_active:
            functions = await repo.papeis_vigentes_em(collaborator.id, reference)
            if any(item.role == "FINALIZACAO" for item in functions):
                return
    raise LancadorDeRecebimentoInvalidoError(
        "Somente Finalização e Financeiro podem lançar recebimentos."
    )


def _require_finance(actor: User) -> None:
    if "FINANCEIRO" not in actor.roles:
        raise LancadorDeRecebimentoInvalidoError("Esta ação é exclusiva do Financeiro.")


@router.get("/receipts", response_model=ReceiptPageResponse)
async def list_receipts(
    actor: Annotated[User, Depends(require_permission("receipts:read"))],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
    receipt_status: Annotated[str | None, Query(alias="status")] = None,
    proposal_id: Annotated[int | None, Query()] = None,
) -> ReceiptPageResponse:
    del actor
    rows = await service.list(status=receipt_status, proposal_id=proposal_id)
    return ReceiptPageResponse(
        items=[
            ReceiptResponse(
                id=row.receipt.id,
                proposal_id=row.receipt.proposal_id,
                customer_name=row.customer_name,
                amount=str(row.receipt.amount),
                business_date=row.receipt.business_date,
                payment_method=row.receipt.payment_method,
                reference=row.receipt.reference,
                notes=row.receipt.notes,
                status=row.receipt.status,
                rejection_reason=row.receipt.rejection_reason,
                proof_file_name=row.receipt.proof_file_name,
                created_at=row.receipt.created_at,
                created_by=row.receipt.created_by,
                creator_name=row.creator_name,
                decided_at=row.receipt.decided_at,
                decided_by=row.receipt.decided_by,
                reversed=row.reversal_reason is not None,
                reversal_reason=row.reversal_reason,
            )
            for row in rows
        ]
    )


@router.post(
    "/proposals/{proposal_id}/receipts",
    response_model=ReceiptWriteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_receipt(
    proposal_id: int,
    request: Request,
    uow: Uow,
    actor: Annotated[User, Depends(require_permission("receipts:write"))],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
    amount: Annotated[Decimal, Form(gt=0, max_digits=18, decimal_places=2)],
    business_date: Annotated[date, Form()],
    payment_method: Annotated[str, Form(min_length=2, max_length=30)],
    proof: Annotated[UploadFile, File()],
    reference: Annotated[str | None, Form(max_length=100)] = None,
    notes: Annotated[str | None, Form(max_length=255)] = None,
) -> ReceiptWriteResponse:
    await _require_launcher(actor, uow, request.app.state.clock.business_date())
    result = await service.create(
        proposal_id=proposal_id,
        amount=amount,
        business_date=business_date,
        payment_method=payment_method,
        reference=reference,
        notes=notes,
        file_name=proof.filename or "comprovante",
        content_type=proof.content_type or "application/octet-stream",
        content=await proof.read(),
        idempotency_key=idempotency_key,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return _write_response(result)


@router.post("/receipts/{receipt_id}/decision", response_model=ReceiptWriteResponse)
async def decide_receipt(
    receipt_id: int,
    body: ReceiptDecisionRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("receipts:approve"))],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> ReceiptWriteResponse:
    _require_finance(actor)
    result = await service.decide(
        receipt_id=receipt_id,
        approve=body.decision is ReceiptDecision.APPROVE,
        reason=body.reason,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return _write_response(result)


@router.post("/receipts/{receipt_id}/reversal", response_model=ReceiptWriteResponse)
async def reverse_receipt(
    receipt_id: int,
    body: ReceiptReversalRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission("reversals:approve"))],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> ReceiptWriteResponse:
    _require_finance(actor)
    result = await service.reverse(
        receipt_id=receipt_id,
        reason=body.reason,
        business_date=body.business_date,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return _write_response(result)


@router.get("/receipts/{receipt_id}/proof")
async def download_proof(
    receipt_id: int,
    request: Request,
    actor: Annotated[User, Depends(require_permission("receipts:read"))],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> Response:
    del actor
    receipt = await service.get(receipt_id)
    storage = ObjectAttachmentStorage(
        request.app.state.storage, request.app.state.settings.storage.object_storage_bucket
    )
    content = await storage.ler(receipt.proof_storage_key)
    return Response(
        content=content,
        media_type=receipt.proof_content_type,
        headers={"Content-Disposition": f'attachment; filename="{receipt.proof_file_name}"'},
    )
