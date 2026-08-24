from __future__ import annotations

from datetime import date, time
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

from app.modules.commercial.api.dependencies import Escopo, get_create_proposal_handler
from app.modules.commercial.api.schemas.proposal import ProposalWithReceiptWriteResponse
from app.modules.commercial.application.commands.create_proposal import (
    CreateProposal,
    CreateProposalHandler,
)
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
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
from app.modules.receivables.application.receipt_service import (
    TAMANHO_MAXIMO,
    ReceiptResult,
    ReceiptService,
)
from app.modules.receivables.domain.errors import (
    LancadorDeRecebimentoInvalidoError,
    RecebimentoInvalidoError,
)
from app.platform.http.content_disposition import content_disposition
from app.platform.http.uploads import read_upload_limited

router = APIRouter(prefix="/api/v1", tags=["receivables"])


async def _read_proof(proof: UploadFile) -> bytes:
    try:
        return await read_upload_limited(proof, max_bytes=TAMANHO_MAXIMO)
    except ValueError as exc:
        raise RecebimentoInvalidoError("O comprovante ultrapassa 10 MB.") from exc


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


@router.post(
    "/proposals/with-receipt",
    response_model=ProposalWithReceiptWriteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_proposal_with_receipt(
    request: Request,
    uow: Uow,
    actor: Annotated[
        User, Depends(require_permission("proposals:write", "receipts:write"))
    ],
    proposal_handler: Annotated[
        CreateProposalHandler, Depends(get_create_proposal_handler)
    ],
    receipt_service: Annotated[ReceiptService, Depends(get_receipt_service)],
    scope: Escopo,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
    consultant_id: Annotated[int, Form()],
    proposal_business_date: Annotated[date, Form()],
    customer_name: Annotated[str, Form(min_length=3, max_length=200)],
    customer_document: Annotated[str, Form(min_length=11, max_length=20)],
    operation_amount: Annotated[Decimal, Form(gt=0, max_digits=18, decimal_places=2)],
    tps_percentage: Annotated[Decimal, Form(ge=0, le=100, max_digits=9, decimal_places=6)],
    amount: Annotated[Decimal, Form(gt=0, max_digits=18, decimal_places=2)],
    payment_business_date: Annotated[date, Form()],
    payment_method: Annotated[str, Form(min_length=2, max_length=30)],
    receiving_account_id: Annotated[int, Form()],
    proof: Annotated[UploadFile, File()],
    external_id: Annotated[str | None, Form(max_length=60)] = None,
    bko_collaborator_id: Annotated[int | None, Form()] = None,
    finalizer_collaborator_id: Annotated[int | None, Form()] = None,
    payment_time: Annotated[time | None, Form()] = None,
) -> ProposalWithReceiptWriteResponse:
    """Persiste proposta e pagamento inicial no mesmo commit de banco."""
    await _require_launcher(actor, uow, request.app.state.clock.business_date())
    correlation_id = getattr(request.state, "correlation_id", None)
    proposal = await proposal_handler.execute(
        CreateProposal(
            consultant_id=consultant_id,
            business_date=proposal_business_date,
            customer_name=customer_name,
            customer_document=customer_document,
            operation_amount=operation_amount,
            tps_percentage=tps_percentage,
            external_id=external_id,
            bko_collaborator_id=bko_collaborator_id,
            finalizer_collaborator_id=finalizer_collaborator_id,
            ator=actor.id,
            correlation_id=correlation_id,
        ),
        commit=False,
    )
    receipt = await receipt_service.create(
        proposal_id=proposal.id,
        amount=amount,
        business_date=payment_business_date,
        payment_time=payment_time,
        payment_method=payment_method,
        receiving_account_id=receiving_account_id,
        reference=None,
        notes=None,
        file_name=proof.filename or "comprovante",
        content_type=proof.content_type or "application/octet-stream",
        content=await _read_proof(proof),
        idempotency_key=idempotency_key,
        actor=actor.id,
        correlation_id=correlation_id,
        scope=scope,
        commit=False,
    )
    try:
        await uow.commit()
    except Exception:
        await receipt_service.discard_uploaded(receipt.receipt.proof_storage_key)
        raise
    return ProposalWithReceiptWriteResponse(
        id=proposal.id,
        status=StatusDaProposta(proposal.status),
        company_commission_amount=str(proposal.company_commission_amount),
        outstanding_amount=str(proposal.outstanding_amount),
        version=proposal.version,
        receipt_id=receipt.receipt.id,
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
    scope: Escopo,
    receipt_status: Annotated[str | None, Query(alias="status")] = None,
    proposal_id: Annotated[int | None, Query()] = None,
) -> ReceiptPageResponse:
    del actor
    rows = await service.list(scope=scope, status=receipt_status, proposal_id=proposal_id)
    return ReceiptPageResponse(
        items=[
            ReceiptResponse(
                id=row.receipt.id,
                proposal_id=row.receipt.proposal_id,
                proposal_approval_status=row.proposal_approval_status,
                customer_name=row.customer_name,
                amount=str(row.receipt.amount),
                business_date=row.receipt.business_date,
                payment_datetime=row.receipt.payment_datetime,
                payment_method=row.receipt.payment_method,
                receiving_account_id=row.receipt.receiving_account_id,
                receiving_account_label=row.receiving_account_label,
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
                reversed=row.reversed_amount > 0,
                reversed_amount=str(row.reversed_amount),
                net_amount=str(row.receipt.amount - row.reversed_amount),
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
    scope: Escopo,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
    amount: Annotated[Decimal, Form(gt=0, max_digits=18, decimal_places=2)],
    business_date: Annotated[date, Form()],
    payment_method: Annotated[str, Form(min_length=2, max_length=30)],
    # obrigatória: o comprovante já diz de onde o dinheiro veio, e o
    # recebimento tem que dizer onde caiu — senão o relatório por conta nasce
    # incompleto sem ninguém perceber
    receiving_account_id: Annotated[int, Form()],
    proof: Annotated[UploadFile, File()],
    payment_time: Annotated[time | None, Form()] = None,
    reference: Annotated[str | None, Form(max_length=100)] = None,
    notes: Annotated[str | None, Form(max_length=255)] = None,
) -> ReceiptWriteResponse:
    await _require_launcher(actor, uow, request.app.state.clock.business_date())
    result = await service.create(
        proposal_id=proposal_id,
        amount=amount,
        business_date=business_date,
        payment_time=payment_time,
        payment_method=payment_method,
        receiving_account_id=receiving_account_id,
        reference=reference,
        notes=notes,
        file_name=proof.filename or "comprovante",
        content_type=proof.content_type or "application/octet-stream",
        content=await _read_proof(proof),
        idempotency_key=idempotency_key,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        scope=scope,
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
    """Conferência avulsa, para o pagamento que chega depois da aprovação.

    O que a Finalização declara antes do envio não passa por aqui: aquilo é
    conferido junto da decisão da proposta, numa aprovação só.
    """
    _require_finance(actor)
    result = await service.decide(
        receipt_id=receipt_id,
        approve=body.decision is ReceiptDecision.APPROVE,
        reason=body.reason,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return _write_response(result)


@router.delete(
    "/receipts/{receipt_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT
)
async def remove_receipt(
    receipt_id: int,
    request: Request,
    uow: Uow,
    actor: Annotated[User, Depends(require_permission("receipts:write"))],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
    scope: Escopo,
) -> None:
    """Remove um recebimento declarado, antes do envio da proposta.

    Não existe decisão própria de recebimento: quem confere o valor é o
    Financeiro, ao aprovar a proposta. O que existe aqui é a correção do que a
    Finalização digitou errado, enquanto ainda dá.
    """
    await _require_launcher(actor, uow, request.app.state.clock.business_date())
    await service.remove(
        receipt_id=receipt_id,
        actor=actor.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        scope=scope,
    )


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
        amount=body.amount,
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
    scope: Escopo,
    preview: bool = False,
) -> Response:
    del actor
    receipt = await service.get(receipt_id, scope=scope)
    storage = ObjectAttachmentStorage(
        request.app.state.storage,
        request.app.state.settings.storage.object_storage_bucket,
        request.app.state.settings.storage.object_storage_prefix,
    )
    content = await storage.ler(receipt.proof_storage_key)
    disposition = "inline" if preview else "attachment"
    return Response(
        content=content,
        media_type=receipt.proof_content_type,
        headers={
            "Content-Disposition": content_disposition(
                receipt.proof_file_name, inline=disposition == "inline"
            )
        },
    )
