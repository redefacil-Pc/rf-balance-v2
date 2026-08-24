"""Processa lotes de PDFs financeiros e publica o ZIP no object storage."""

from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commissions.application.queries.financial_report import (
    FinancialCommissionReportQuery,
)
from app.modules.documents.infrastructure.models.document_models import (
    DocumentJobModel,
    StoredDocumentModel,
)
from app.modules.reporting.application.financial_report_documents import financial_report_pdf
from app.platform.config.storage import StorageSettings
from app.platform.storage.object_storage import chave_com_prefixo
from app.platform.time.clock import Clock

_logger = structlog.get_logger("worker.documents")
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


class FinancialReportBatchProcessor:
    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: Any,
        storage_settings: StorageSettings,
        clock: Clock,
    ) -> None:
        self._session = session
        self._storage = storage
        self._settings = storage_settings
        self._clock = clock

    async def process_next(self) -> bool:
        job = await self._claim_next()
        if job is None:
            return False
        try:
            await self._process(job)
        except Exception as exc:
            await self._session.rollback()
            await self._mark_failure(job.id, exc)
            _logger.exception("document_job_failed", job_id=job.id, attempt=job.attempt_count)
        return True

    async def _claim_next(self) -> DocumentJobModel | None:
        now = self._clock.now()
        stale_before = now - timedelta(minutes=15)
        stale_jobs = list(
            (
                await self._session.scalars(
                    select(DocumentJobModel).where(
                        DocumentJobModel.status == "RUNNING",
                        DocumentJobModel.started_at < stale_before,
                    )
                )
            ).all()
        )
        for stale in stale_jobs:
            stale.status = "FAILED"
            stale.error_message = "Processamento interrompido; lote liberado para nova tentativa."
            stale.next_attempt_at = now
        if stale_jobs:
            await self._session.commit()

        job = await self._session.scalar(
            select(DocumentJobModel)
            .where(
                DocumentJobModel.job_type == "COMMISSION_REPORT_BATCH",
                DocumentJobModel.attempt_count < DocumentJobModel.max_attempts,
                or_(
                    DocumentJobModel.status == "PENDING",
                    (
                        (DocumentJobModel.status == "FAILED")
                        & (DocumentJobModel.next_attempt_at <= now)
                    ),
                ),
            )
            .order_by(DocumentJobModel.created_at, DocumentJobModel.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            await self._session.rollback()
            return None
        job.status = "RUNNING"
        job.attempt_count += 1
        job.started_at = now
        job.next_attempt_at = None
        job.error_message = None
        await self._session.commit()
        return job

    async def _process(self, job: DocumentJobModel) -> None:
        summary, beneficiaries = await FinancialCommissionReportQuery(self._session).summary(
            period_start=job.period_start,
            period_end=job.period_end,
            unit_id=job.unit_id,
            leader_id=job.leader_id,
        )
        job.total_items = len(beneficiaries)
        job.processed_items = 0
        await self._session.commit()

        archive_buffer = BytesIO()
        with ZipFile(archive_buffer, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("resumo-financeiro.pdf", financial_report_pdf(summary, beneficiaries))
            for index, beneficiary in enumerate(beneficiaries, start=1):
                pdf = financial_report_pdf(summary, [beneficiary])
                file_name = (
                    f"{beneficiary.beneficiary_id:06d}-"
                    f"{self._safe_name(beneficiary.beneficiary_name)}.pdf"
                )
                archive.writestr(file_name, pdf)
                await self._store_document(
                    job=job,
                    document_key=f"beneficiary-{beneficiary.beneficiary_id}",
                    kind="BENEFICIARY_PDF",
                    beneficiary_id=beneficiary.beneficiary_id,
                    file_name=file_name,
                    content_type="application/pdf",
                    content=pdf,
                )
                job.processed_items = index
                await self._session.commit()

        archive_content = archive_buffer.getvalue()
        archive_name = f"relatorios-comissoes-lote-{job.id}.zip"
        await self._store_document(
            job=job,
            document_key="archive",
            kind="ARCHIVE",
            beneficiary_id=None,
            file_name=archive_name,
            content_type="application/zip",
            content=archive_content,
        )
        job.status = "COMPLETED"
        job.completed_at = self._clock.now()
        job.error_message = None
        await self._session.commit()
        _logger.info(
            "document_job_completed",
            job_id=job.id,
            documents=job.total_items,
            size_bytes=len(archive_content),
        )

    async def _store_document(
        self,
        *,
        job: DocumentJobModel,
        document_key: str,
        kind: str,
        beneficiary_id: int | None,
        file_name: str,
        content_type: str,
        content: bytes,
    ) -> None:
        storage_key = chave_com_prefixo(
            f"generated/commission-reports/{job.id}/{document_key}",
            self._settings.object_storage_prefix,
        )
        self._storage.put_object(
            Bucket=self._settings.object_storage_bucket,
            Key=storage_key,
            Body=content,
            ContentType=content_type,
            Metadata={"sha256": hashlib.sha256(content).hexdigest()},
        )
        document = await self._session.scalar(
            select(StoredDocumentModel).where(
                StoredDocumentModel.job_id == job.id,
                StoredDocumentModel.document_key == document_key,
            )
        )
        digest = hashlib.sha256(content).hexdigest()
        if document is None:
            self._session.add(
                StoredDocumentModel(
                    job_id=job.id,
                    document_key=document_key,
                    kind=kind,
                    beneficiary_id=beneficiary_id,
                    file_name=file_name,
                    content_type=content_type,
                    size_bytes=len(content),
                    storage_key=storage_key,
                    sha256=digest,
                )
            )
        else:
            document.file_name = file_name
            document.content_type = content_type
            document.size_bytes = len(content)
            document.sha256 = digest

    async def _mark_failure(self, job_id: int, exc: Exception) -> None:
        job = await self._session.get(DocumentJobModel, job_id)
        if job is None:
            return
        job.error_message = str(exc)[:2000]
        if job.attempt_count >= job.max_attempts:
            job.status = "DEAD_LETTER"
            job.next_attempt_at = None
        else:
            job.status = "FAILED"
            job.next_attempt_at = self._clock.now() + timedelta(
                seconds=min(2**job.attempt_count, 300)
            )
        await self._session.commit()

    @staticmethod
    def _safe_name(value: str) -> str:
        normalized = _SAFE_NAME.sub("-", value.strip()).strip("-._")
        return normalized[:80] or "beneficiario"
