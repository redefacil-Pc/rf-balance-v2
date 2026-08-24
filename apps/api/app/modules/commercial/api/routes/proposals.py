"""Rotas de propostas."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status

from app.modules.commercial.api.dependencies import (
    Escopo,
    get_add_attachment_handler,
    get_cancel_proposal_handler,
    get_create_proposal_handler,
    get_decide_proposal_handler,
    get_get_attachment_content_handler,
    get_get_proposal_handler,
    get_list_attachments_handler,
    get_list_proposals_handler,
    get_remove_attachment_handler,
    get_submit_proposal_handler,
    get_update_proposal_handler,
)
from app.modules.commercial.api.schemas.attachment import (
    AttachmentResponse,
    AttachmentUploadResponse,
)
from app.modules.commercial.api.schemas.proposal import (
    CancelProposalRequest,
    DecisionRequest,
    DecisionResponse,
    PendingProposalCountResponse,
    ProposalCancelResponse,
    ProposalDetailResponse,
    ProposalPageResponse,
    ProposalRequest,
    ProposalResponse,
    ProposalWriteResponse,
    SubmitProposalRequest,
    SubmitProposalResponse,
    UpdateProposalRequest,
)
from app.modules.commercial.application.commands.add_proposal_attachment import (
    AddProposalAttachment,
    AddProposalAttachmentHandler,
)
from app.modules.commercial.application.commands.cancel_proposal import (
    CancelProposal,
    CancelProposalHandler,
)
from app.modules.commercial.application.commands.create_proposal import (
    CreateProposal,
    CreateProposalHandler,
)
from app.modules.commercial.application.commands.decide_proposal import (
    DecideProposal,
    DecideProposalHandler,
)
from app.modules.commercial.application.commands.remove_proposal_attachment import (
    RemoveProposalAttachment,
    RemoveProposalAttachmentHandler,
)
from app.modules.commercial.application.commands.submit_proposal import (
    SubmitProposal,
    SubmitProposalHandler,
)
from app.modules.commercial.application.commands.update_proposal import (
    UpdateProposal,
    UpdateProposalHandler,
)
from app.modules.commercial.application.queries.get_attachment_content import (
    GetAttachmentContent,
    GetAttachmentContentHandler,
)
from app.modules.commercial.application.queries.get_proposal import GetProposal, GetProposalHandler
from app.modules.commercial.application.queries.list_proposal_attachments import (
    ListProposalAttachments,
    ListProposalAttachmentsHandler,
)
from app.modules.commercial.application.queries.list_proposals import (
    ListProposals,
    ListProposalsHandler,
)
from app.modules.commercial.domain.errors import ComprovanteInvalidoError
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import SituacaoDeAprovacao
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    FiltroDePropostas,
)
from app.modules.identity.api.dependencies import require_permission
from app.modules.identity.domain.entities.user import User
from app.platform.http.content_disposition import content_disposition
from app.platform.http.pagination import Cursor, normalizar_limite
from app.platform.http.uploads import read_upload_limited

router = APIRouter(prefix="/api/v1/proposals", tags=["commercial"])

PERMISSAO_DE_PII = "proposals:read_pii"


@router.post("", response_model=ProposalWriteResponse, status_code=status.HTTP_201_CREATED)
async def criar(
    body: ProposalRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("proposals:write"))],
    handler: Annotated[CreateProposalHandler, Depends(get_create_proposal_handler)],
) -> ProposalWriteResponse:
    resultado = await handler.execute(
        CreateProposal(
            consultant_id=body.consultant_id,
            business_date=body.business_date,
            customer_name=body.customer_name,
            customer_document=body.customer_document,
            operation_amount=body.operation_amount,
            tps_percentage=body.tps_percentage,
            external_id=body.external_id,
            bko_collaborator_id=body.bko_collaborator_id,
            finalizer_collaborator_id=body.finalizer_collaborator_id,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return ProposalWriteResponse(
        id=resultado.id,
        status=StatusDaProposta(resultado.status),
        company_commission_amount=str(resultado.company_commission_amount),
        outstanding_amount=str(resultado.outstanding_amount),
        version=resultado.version,
    )


@router.get("", response_model=ProposalPageResponse)
async def listar(
    request: Request,
    ator: Annotated[User, Depends(require_permission("proposals:read"))],
    escopo: Escopo,
    handler: Annotated[ListProposalsHandler, Depends(get_list_proposals_handler)],
    proposal_status: Annotated[StatusDaProposta | None, Query(alias="status")] = None,
    approval_status: Annotated[SituacaoDeAprovacao | None, Query()] = None,
    exclude_approval_status: Annotated[SituacaoDeAprovacao | None, Query()] = None,
    consultant_id: Annotated[int | None, Query()] = None,
    bko_collaborator_id: Annotated[int | None, Query()] = None,
    finalizer_collaborator_id: Annotated[int | None, Query()] = None,
    external_id: Annotated[str | None, Query(max_length=60)] = None,
    customer_name: Annotated[str | None, Query(max_length=200)] = None,
    business_date_from: Annotated[date | None, Query()] = None,
    business_date_to: Annotated[date | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    cursor: Annotated[str | None, Query()] = None,
) -> ProposalPageResponse:
    pagina = await handler.execute(
        ListProposals(
            filtro=FiltroDePropostas(
                status=proposal_status.value if proposal_status else None,
                approval_status=approval_status.value if approval_status else None,
                exclude_approval_status=(
                    exclude_approval_status.value if exclude_approval_status else None
                ),
                consultant_id=consultant_id,
                bko_collaborator_id=bko_collaborator_id,
                finalizer_collaborator_id=finalizer_collaborator_id,
                de=business_date_from,
                ate=business_date_to,
                external_id=external_id,
                busca_por_cliente=customer_name,
                escopo=escopo,
            ),
            limite=normalizar_limite(limit),
            cursor=Cursor.decodificar(cursor) if cursor else None,
            pode_ver_pii=ator.pode(PERMISSAO_DE_PII),
        )
    )
    return ProposalPageResponse(
        # `asdict`, não `vars`: os DTOs usam `slots=True` e não têm `__dict__`
        items=[ProposalResponse(**asdict(item)) for item in pagina.itens],
        next_cursor=pagina.proximo_cursor,
    )


@router.get("/pending-count", response_model=PendingProposalCountResponse)
async def contar_pendentes(
    _ator: Annotated[User, Depends(require_permission("proposals:approve"))],
    escopo: Escopo,
    handler: Annotated[ListProposalsHandler, Depends(get_list_proposals_handler)],
) -> PendingProposalCountResponse:
    quantidade = await handler.count(
        FiltroDePropostas(approval_status="SUBMITTED", escopo=escopo)
    )
    return PendingProposalCountResponse(count=quantidade)


@router.get("/{proposal_id}", response_model=ProposalDetailResponse)
async def detalhar(
    proposal_id: int,
    ator: Annotated[User, Depends(require_permission("proposals:read"))],
    escopo: Escopo,
    handler: Annotated[GetProposalHandler, Depends(get_get_proposal_handler)],
) -> ProposalDetailResponse:
    detalhe = await handler.execute(
        GetProposal(
            proposal_id=proposal_id,
            pode_ver_pii=ator.pode(PERMISSAO_DE_PII),
            escopo=escopo,
        )
    )
    return ProposalDetailResponse(**asdict(detalhe))


@router.put("/{proposal_id}", response_model=ProposalWriteResponse)
async def alterar(
    proposal_id: int,
    body: UpdateProposalRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("proposals:write"))],
    handler: Annotated[UpdateProposalHandler, Depends(get_update_proposal_handler)],
) -> ProposalWriteResponse:
    resultado = await handler.execute(
        UpdateProposal(
            proposal_id=proposal_id,
            version=body.version,
            operation_amount=body.operation_amount,
            tps_percentage=body.tps_percentage,
            bko_collaborator_id=body.bko_collaborator_id,
            finalizer_collaborator_id=body.finalizer_collaborator_id,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return ProposalWriteResponse(
        id=resultado.id,
        status=StatusDaProposta(resultado.status),
        company_commission_amount=str(resultado.company_commission_amount),
        outstanding_amount=str(resultado.outstanding_amount),
        version=resultado.version,
    )


@router.post("/{proposal_id}/cancellation", response_model=ProposalCancelResponse)
async def cancelar(
    proposal_id: int,
    body: CancelProposalRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("proposals:write"))],
    handler: Annotated[CancelProposalHandler, Depends(get_cancel_proposal_handler)],
) -> ProposalCancelResponse:
    resultado = await handler.execute(
        CancelProposal(
            proposal_id=proposal_id,
            version=body.version,
            motivo=body.reason,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return ProposalCancelResponse(
        id=resultado.id, status=StatusDaProposta(resultado.status), version=resultado.version
    )


@router.post("/{proposal_id}/submission", response_model=SubmitProposalResponse)
async def enviar_para_aprovacao(
    proposal_id: int,
    body: SubmitProposalRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("proposals:write"))],
    handler: Annotated[SubmitProposalHandler, Depends(get_submit_proposal_handler)],
) -> SubmitProposalResponse:
    resultado = await handler.execute(
        SubmitProposal(
            proposal_id=proposal_id,
            version=body.version,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return SubmitProposalResponse(
        id=resultado.id,
        approval_status=SituacaoDeAprovacao(resultado.approval_status),
        version=resultado.version,
    )


@router.post("/{proposal_id}/decision", response_model=DecisionResponse)
async def decidir(
    proposal_id: int,
    body: DecisionRequest,
    request: Request,
    ator: Annotated[User, Depends(require_permission("proposals:approve"))],
    handler: Annotated[DecideProposalHandler, Depends(get_decide_proposal_handler)],
) -> DecisionResponse:
    resultado = await handler.execute(
        DecideProposal(
            proposal_id=proposal_id,
            version=body.version,
            decisao=body.decision,
            motivo=body.reason,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return DecisionResponse(
        id=resultado.id,
        approval_status=SituacaoDeAprovacao(resultado.approval_status),
        rejection_reason=resultado.rejection_reason,
        version=resultado.version,
    )


@router.get("/{proposal_id}/attachments", response_model=list[AttachmentResponse])
async def listar_anexos(
    proposal_id: int,
    ator: Annotated[User, Depends(require_permission("proposals:read"))],
    escopo: Escopo,
    handler: Annotated[ListProposalAttachmentsHandler, Depends(get_list_attachments_handler)],
) -> list[AttachmentResponse]:
    anexos = await handler.execute(ListProposalAttachments(proposal_id=proposal_id, escopo=escopo))
    return [AttachmentResponse(**asdict(anexo)) for anexo in anexos]


@router.post(
    "/{proposal_id}/attachments",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def anexar_comprovante(
    proposal_id: int,
    request: Request,
    ator: Annotated[User, Depends(require_permission("proposals:write"))],
    handler: Annotated[AddProposalAttachmentHandler, Depends(get_add_attachment_handler)],
    file: Annotated[UploadFile, File()],
) -> AttachmentUploadResponse:
    try:
        conteudo = await read_upload_limited(file, max_bytes=10 * 1024 * 1024)
    except ValueError as exc:
        raise ComprovanteInvalidoError("O arquivo passa de 10 MB.") from exc
    resultado = await handler.execute(
        AddProposalAttachment(
            proposal_id=proposal_id,
            file_name=file.filename or "comprovante",
            content_type=file.content_type or "application/octet-stream",
            conteudo=conteudo,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    return AttachmentUploadResponse(**asdict(resultado))


@router.get("/{proposal_id}/attachments/{attachment_id}")
async def baixar_comprovante(
    proposal_id: int,
    attachment_id: int,
    ator: Annotated[User, Depends(require_permission("proposals:read"))],
    escopo: Escopo,
    handler: Annotated[GetAttachmentContentHandler, Depends(get_get_attachment_content_handler)],
) -> Response:
    conteudo = await handler.execute(
        GetAttachmentContent(proposal_id=proposal_id, attachment_id=attachment_id, escopo=escopo)
    )
    return Response(
        content=conteudo.conteudo,
        media_type=conteudo.content_type,
        headers={"Content-Disposition": content_disposition(conteudo.file_name)},
    )


@router.delete(
    "/{proposal_id}/attachments/{attachment_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remover_comprovante(
    proposal_id: int,
    attachment_id: int,
    request: Request,
    ator: Annotated[User, Depends(require_permission("proposals:write"))],
    handler: Annotated[RemoveProposalAttachmentHandler, Depends(get_remove_attachment_handler)],
) -> None:
    await handler.execute(
        RemoveProposalAttachment(
            proposal_id=proposal_id,
            attachment_id=attachment_id,
            ator=ator.id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
