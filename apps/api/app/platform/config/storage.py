"""Configuração do object storage (PDFs, exportações e backups)."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    object_storage_endpoint: str = "http://minio:9000"
    object_storage_bucket: str = "rfbalance-documents"
    object_storage_access_key: str = ""
    object_storage_secret_key: str = ""
    object_storage_region: str = "us-east-1"
    object_storage_addressing_style: Literal["path", "virtual"] = "path"
    object_storage_prefix: str = ""

    # O backup pode compartilhar o Space dos documentos, mas fica isolado em
    # outro prefixo. Bucket vazio desliga o agendamento sem afetar a API.
    backup_bucket: str = ""
    backup_prefix: str = "backups"
    backup_retention_days: int = Field(default=30, ge=1, le=3650)
    backup_hour_utc: int = Field(default=6, ge=0, le=23)
    backup_restore_database: str = "rfbalance_restore_check"
    backup_restore_drill_weekday: int = Field(default=6, ge=0, le=6)
    backup_restore_drill_hour_utc: int = Field(default=7, ge=0, le=23)
    backup_local_replica_dir: str = ""
