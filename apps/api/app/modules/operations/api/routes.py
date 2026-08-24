"""Consulta operacional e acionamento manual de backup."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.identity.api.dependencies import Uow, require_permission
from app.modules.identity.domain.entities.user import User
from app.modules.operations.api.schemas import (
    BackupExecutionResponse,
    BackupStatus,
    BackupSummary,
    IntegrityCheckSummary,
    OperationsStatusResponse,
)
from app.modules.operations.domain.errors import BackupEmAndamentoError
from app.platform.db.data_integrity_check_model import DataIntegrityCheckModel
from app.platform.storage.object_storage import chave_com_prefixo
from worker.jobs.backup.database_backup import BackupResult, create_database_backup

router = APIRouter(prefix="/api/v1/admin/operations", tags=["operations"])


def _list_backup_objects(storage: Any, bucket: str, prefix: str) -> list[dict[str, Any]]:
    paginator = storage.get_paginator("list_objects_v2")
    objects: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix.rstrip('/')}/database/"):
        objects.extend(item for item in page.get("Contents", []) if item["Key"].endswith(".sql.gz"))
    return objects


def _last_backup(storage: Any, bucket: str, prefix: str) -> BackupSummary | None:
    objects = _list_backup_objects(storage, bucket, prefix)
    if not objects:
        return None
    latest = max(objects, key=lambda item: item["LastModified"])
    head = storage.head_object(Bucket=bucket, Key=latest["Key"])
    sha256 = head.get("Metadata", {}).get("sha256")
    verified = False
    try:
        manifest_response = storage.get_object(Bucket=bucket, Key=f"{latest['Key']}.json")
        manifest = json.loads(manifest_response["Body"].read())
        verified = bool(
            manifest.get("verified_after_upload") is True
            and manifest.get("object_key") == latest["Key"]
            and manifest.get("sha256") == sha256
        )
    except Exception:
        verified = False
    return BackupSummary(
        key=latest["Key"],
        created_at=latest["LastModified"].astimezone(UTC),
        compressed_bytes=int(latest["Size"]),
        sha256=sha256,
        verified=verified,
    )


def _versioning_enabled(storage: Any, bucket: str) -> bool:
    status = storage.get_bucket_versioning(Bucket=bucket).get("Status")
    return str(status or "") == "Enabled"


async def _integrity_status(uow: Uow) -> list[IntegrityCheckSummary]:
    rows = (
        await uow.session.scalars(
            select(DataIntegrityCheckModel).order_by(
                DataIntegrityCheckModel.checked_at.desc(), DataIntegrityCheckModel.id.desc()
            )
        )
    ).all()
    latest: dict[str, DataIntegrityCheckModel] = {}
    for row in rows:
        latest.setdefault(row.check_type, row)
    return [
        IntegrityCheckSummary(
            check_type=row.check_type,
            status=row.status,
            count=int(row.details.get("count", 0)),
            checked_at=row.checked_at,
        )
        for row in latest.values()
    ]


@router.get("", response_model=OperationsStatusResponse)
async def get_operations_status(
    request: Request,
    uow: Uow,
    actor: Annotated[User, Depends(require_permission("admin:operations"))],
) -> OperationsStatusResponse:
    del actor
    settings = request.app.state.settings.storage
    last = None
    if settings.backup_bucket:
        last = await asyncio.to_thread(
            _last_backup,
            request.app.state.storage,
            settings.backup_bucket,
            settings.backup_prefix,
        )
    versioning_enabled = bool(settings.backup_bucket) and await asyncio.to_thread(
        _versioning_enabled, request.app.state.storage, settings.backup_bucket
    )
    return OperationsStatusResponse(
        backup=BackupStatus(
            enabled=bool(settings.backup_bucket),
            prefix=chave_com_prefixo("database", settings.backup_prefix),
            retention_days=settings.backup_retention_days,
            schedule_hour_utc=settings.backup_hour_utc,
            last_backup=last,
            versioning_enabled=versioning_enabled,
            local_replica_enabled=bool(settings.backup_local_replica_dir),
        ),
        integrity_checks=await _integrity_status(uow),
    )


@router.post(
    "/backups",
    response_model=BackupExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_backup(
    request: Request,
    uow: Uow,
    actor: Annotated[User, Depends(require_permission("admin:operations", "backups:run"))],
) -> BackupExecutionResponse:
    lock_key = "rfbalance:backup:manual-lock"
    lock_token = uuid.uuid4().hex
    acquired = await request.app.state.redis.set(lock_key, lock_token, ex=1800, nx=True)
    if not acquired:
        raise BackupEmAndamentoError()
    try:
        result: BackupResult = await asyncio.to_thread(
            create_database_backup, request.app.state.settings
        )
    finally:
        await request.app.state.redis.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end",
            1,
            lock_key,
            lock_token,
        )
    SqlAuditRecorder(uow.session, request.app.state.clock).registrar(
        module="operations",
        action="backup.created_manually",
        actor_user_id=actor.id,
        actor_label=actor.full_name,
        aggregate_type="database_backup",
        aggregate_id=result.key,
        correlation_id=getattr(request.state, "correlation_id", None),
        payload={
            "compressed_bytes": result.compressed_bytes,
            "sha256": result.sha256,
            "removed_by_retention": result.removed_by_retention,
        },
    )
    await uow.commit()
    return BackupExecutionResponse(
        key=result.key,
        created_at=result.created_at,
        compressed_bytes=result.compressed_bytes,
        sha256=result.sha256,
        removed_by_retention=result.removed_by_retention,
        local_replica_created=result.local_replica_path is not None,
    )
