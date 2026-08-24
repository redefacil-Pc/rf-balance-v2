from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import exists, select

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.documents.api.schemas.document_job import (
    CreateDocumentJobRequest,
    DocumentJobPageResponse,
    DocumentJobResponse,
)
from app.modules.documents.application.document_job_service import (
    CreateDocumentJob,
    DocumentJobService,
)
from app.modules.documents.domain.errors import DocumentJobNotFoundError, DocumentNotReadyError
from app.modules.documents.infrastructure.models.document_models import (
    DocumentJobModel,
    StoredDocumentModel,
)
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User
from app.platform.http.content_disposition import content_disposition

router = APIRouter(prefix="/api/v1/document-jobs", tags=["documents"])


def _response(job: DocumentJobModel, archive_ready: bool) -> DocumentJobResponse:
    return DocumentJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        period_start=job.period_start,
        period_end=job.period_end,
        unit_id=job.unit_id,
        leader_id=job.leader_id,
        total_items=job.total_items,
        processed_items=job.processed_items,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        error_message=job.error_message,
        archive_ready=archive_ready,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post("", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_document_job(
    body: CreateDocumentJobRequest,
    request: Request,
    uow: Uow,
    actor: Annotated[User, Depends(require_permission("reports:export", "settlements:read"))],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
) -> DocumentJobResponse:
    job = await DocumentJobService(
        uow.session, SqlAuditRecorder(uow.session, request.app.state.clock)
    ).create(
        CreateDocumentJob(
            period_start=body.period_start,
            period_end=body.period_end,
            unit_id=body.unit_id,
            leader_id=body.leader_id,
            idempotency_key=idempotency_key,
            requested_by=actor.id,
            actor_label=str(actor.email),
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    )
    archive_ready = await uow.session.scalar(
        select(StoredDocumentModel.id).where(
            StoredDocumentModel.job_id == job.id,
            StoredDocumentModel.kind == "ARCHIVE",
        )
    )
    return _response(job, archive_ready is not None)


@router.get("", response_model=DocumentJobPageResponse)
async def list_document_jobs(
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("reports:export", "settlements:read"))],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentJobPageResponse:
    archive_exists = exists(
        select(StoredDocumentModel.id).where(
            StoredDocumentModel.job_id == DocumentJobModel.id,
            StoredDocumentModel.kind == "ARCHIVE",
        )
    )
    rows = (
        await uow.session.execute(
            select(DocumentJobModel, archive_exists.label("archive_ready"))
            .order_by(DocumentJobModel.created_at.desc(), DocumentJobModel.id.desc())
            .limit(limit)
        )
    ).all()
    return DocumentJobPageResponse(
        items=[_response(job, bool(archive_ready)) for job, archive_ready in rows]
    )


@router.get("/{job_id}", response_model=DocumentJobResponse)
async def get_document_job(
    job_id: int,
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("reports:export", "settlements:read"))],
) -> DocumentJobResponse:
    job = await uow.session.get(DocumentJobModel, job_id)
    if job is None:
        raise DocumentJobNotFoundError("O lote solicitado não existe.")
    archive_ready = await uow.session.scalar(
        select(StoredDocumentModel.id).where(
            StoredDocumentModel.job_id == job_id,
            StoredDocumentModel.kind == "ARCHIVE",
        )
    )
    return _response(job, archive_ready is not None)


@router.get("/{job_id}/download")
async def download_document_job(
    job_id: int,
    request: Request,
    uow: Uow,
    _actor: Annotated[User, Depends(require_permission("reports:export", "settlements:read"))],
) -> StreamingResponse:
    job = await uow.session.get(DocumentJobModel, job_id)
    if job is None:
        raise DocumentJobNotFoundError("O lote solicitado não existe.")
    document = await uow.session.scalar(
        select(StoredDocumentModel).where(
            StoredDocumentModel.job_id == job_id,
            StoredDocumentModel.kind == "ARCHIVE",
        )
    )
    if document is None or job.status != "COMPLETED":
        raise DocumentNotReadyError("A geração do ZIP ainda não foi concluída.")
    storage: Any = request.app.state.storage
    stored = await asyncio.to_thread(
        storage.get_object,
        Bucket=request.app.state.settings.storage.object_storage_bucket,
        Key=document.storage_key,
    )
    return StreamingResponse(
        stored["Body"].iter_chunks(chunk_size=64 * 1024),
        media_type=document.content_type,
        headers={
            "Content-Disposition": content_disposition(document.file_name),
            "Content-Length": str(document.size_bytes),
        },
    )
