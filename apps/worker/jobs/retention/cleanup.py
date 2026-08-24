from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.infrastructure.models.proposal_attachment_model import (
    ProposalAttachmentModel,
)
from app.modules.documents.infrastructure.models.document_models import (
    DocumentJobModel,
    StoredDocumentModel,
)
from app.modules.receivables.infrastructure.models.receipt_model import ReceiptModel
from app.platform.bus.outbox_model import OutboxEventModel
from app.platform.config.retention import RetentionSettings
from app.platform.config.storage import StorageSettings
from app.platform.db.data_integrity_check_model import DataIntegrityCheckModel
from app.platform.storage.object_storage import chave_com_prefixo


async def execute(
    session: AsyncSession,
    *,
    storage: Any,
    storage_settings: StorageSettings,
    retention: RetentionSettings,
    now: datetime,
) -> dict[str, int]:
    integrity_cutoff = now - timedelta(days=retention.integrity_retention_days)
    outbox_cutoff = now - timedelta(days=retention.outbox_retention_days)
    document_cutoff = now - timedelta(days=retention.generated_document_retention_days)

    integrity = await session.execute(
        delete(DataIntegrityCheckModel).where(
            DataIntegrityCheckModel.checked_at < integrity_cutoff
        )
    )
    outbox = await session.execute(
        delete(OutboxEventModel).where(
            OutboxEventModel.processed_at.is_not(None),
            OutboxEventModel.processed_at < outbox_cutoff,
        )
    )

    documents = list(
        (
            await session.scalars(
                select(StoredDocumentModel).where(
                    StoredDocumentModel.created_at < document_cutoff
                )
            )
        ).all()
    )
    removed_documents = 0
    for document in documents:
        try:
            await asyncio.to_thread(
                storage.delete_object,
                Bucket=storage_settings.object_storage_bucket,
                Key=chave_com_prefixo(
                    document.storage_key, storage_settings.object_storage_prefix
                ),
            )
        except Exception:
            continue
        await session.delete(document)
        removed_documents += 1
    await session.flush()
    jobs = await session.execute(
        delete(DocumentJobModel).where(
            DocumentJobModel.created_at < document_cutoff,
            DocumentJobModel.status.in_(("COMPLETED", "FAILED")),
            ~exists(
                select(StoredDocumentModel.id).where(
                    StoredDocumentModel.job_id == DocumentJobModel.id
                )
            ),
        )
    )

    referenced = set(
        await session.scalars(select(ReceiptModel.proof_storage_key))
    )
    referenced.update(await session.scalars(select(ProposalAttachmentModel.storage_key)))
    referenced.update(await session.scalars(select(StoredDocumentModel.storage_key)))
    removed_orphans = await asyncio.to_thread(
        _remove_orphans,
        storage,
        storage_settings,
        referenced,
        now - timedelta(hours=retention.orphan_storage_grace_hours),
    )
    await session.commit()
    return {
        "integrity_rows": int(integrity.rowcount or 0),
        "outbox_rows": int(outbox.rowcount or 0),
        "documents": removed_documents,
        "document_jobs": int(jobs.rowcount or 0),
        "orphan_objects": removed_orphans,
    }


def _remove_orphans(
    storage: Any,
    settings: StorageSettings,
    referenced: set[str],
    cutoff: datetime,
) -> int:
    removed = 0
    for namespace in ("receipts/", "proposals/"):
        physical_prefix = chave_com_prefixo(namespace, settings.object_storage_prefix)
        paginator = storage.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=settings.object_storage_bucket, Prefix=physical_prefix
        ):
            for item in page.get("Contents", []):
                physical_key = str(item["Key"])
                relative_key = _relative_key(physical_key, settings.object_storage_prefix)
                if relative_key in referenced or item["LastModified"] >= cutoff:
                    continue
                storage.delete_object(
                    Bucket=settings.object_storage_bucket, Key=physical_key
                )
                removed += 1
    return removed


def _relative_key(physical_key: str, prefix: str) -> str:
    normalized = prefix.strip().strip("/")
    marker = f"{normalized}/" if normalized else ""
    return physical_key.removeprefix(marker)
