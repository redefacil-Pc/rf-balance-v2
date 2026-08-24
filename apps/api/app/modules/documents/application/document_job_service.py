"""Criação idempotente e consultas dos lotes de documentos financeiros."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.documents.domain.errors import DocumentIdempotencyConflictError
from app.modules.documents.infrastructure.models.document_models import DocumentJobModel
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.models.unit_model import UnitModel
from app.platform.errors.domain_error import DomainError


class InvalidDocumentScopeError(DomainError):
    code = "invalid-document-scope"
    title = "Recorte de documentos inválido"


@dataclass(frozen=True, slots=True)
class CreateDocumentJob:
    period_start: date
    period_end: date
    unit_id: int | None
    leader_id: int | None
    idempotency_key: str
    requested_by: int
    actor_label: str
    correlation_id: str | None


class DocumentJobService:
    def __init__(self, session: AsyncSession, audit: SqlAuditRecorder) -> None:
        self._session = session
        self._audit = audit

    async def create(self, command: CreateDocumentJob) -> DocumentJobModel:
        await self._validate_scope(command.unit_id, command.leader_id)
        request_hash = self._request_hash(command)
        existing = await self._session.scalar(
            select(DocumentJobModel).where(
                DocumentJobModel.requested_by == command.requested_by,
                DocumentJobModel.idempotency_key == command.idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise DocumentIdempotencyConflictError(
                    "A chave já foi usada para solicitar outro lote."
                )
            return existing

        job = DocumentJobModel(
            job_type="COMMISSION_REPORT_BATCH",
            status="PENDING",
            period_start=command.period_start,
            period_end=command.period_end,
            unit_id=command.unit_id,
            leader_id=command.leader_id,
            total_items=0,
            processed_items=0,
            attempt_count=0,
            max_attempts=3,
            idempotency_key=command.idempotency_key,
            request_hash=request_hash,
            requested_by=command.requested_by,
        )
        self._session.add(job)
        await self._session.flush()
        self._audit.registrar(
            module="documents",
            action="document_job.requested",
            actor_user_id=command.requested_by,
            actor_label=command.actor_label,
            aggregate_type="document_job",
            aggregate_id=str(job.id),
            correlation_id=command.correlation_id,
            payload={
                "period_start": command.period_start.isoformat(),
                "period_end": command.period_end.isoformat(),
                "unit_id": command.unit_id,
                "leader_id": command.leader_id,
            },
        )
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def _validate_scope(self, unit_id: int | None, leader_id: int | None) -> None:
        if unit_id is not None and leader_id is not None:
            raise InvalidDocumentScopeError("Selecione apenas unidade ou equipe.")
        if unit_id is not None and await self._session.get(UnitModel, unit_id) is None:
            raise InvalidDocumentScopeError("A unidade selecionada não existe.")
        if leader_id is not None and await self._session.get(CollaboratorModel, leader_id) is None:
            raise InvalidDocumentScopeError("O líder selecionado não existe.")

    @staticmethod
    def _request_hash(command: CreateDocumentJob) -> str:
        payload = json.dumps(
            {
                "period_start": command.period_start.isoformat(),
                "period_end": command.period_end.isoformat(),
                "unit_id": command.unit_id,
                "leader_id": command.leader_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()
