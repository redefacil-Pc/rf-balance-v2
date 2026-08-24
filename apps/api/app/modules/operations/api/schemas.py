"""Contratos HTTP das operações administrativas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BackupSummary(BaseModel):
    key: str
    created_at: datetime
    compressed_bytes: int
    sha256: str | None
    verified: bool


class BackupStatus(BaseModel):
    enabled: bool
    prefix: str
    retention_days: int
    schedule_hour_utc: int
    last_backup: BackupSummary | None
    versioning_enabled: bool
    local_replica_enabled: bool


class IntegrityCheckSummary(BaseModel):
    check_type: str
    status: str
    count: int
    checked_at: datetime


class OperationsStatusResponse(BaseModel):
    backup: BackupStatus
    integrity_checks: list[IntegrityCheckSummary]


class BackupExecutionResponse(BaseModel):
    key: str
    created_at: datetime
    compressed_bytes: int
    sha256: str
    removed_by_retention: int
    local_replica_created: bool
