"""Configuração do object storage (PDFs, exportações e backups)."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    object_storage_endpoint: str = "http://minio:9000"
    object_storage_bucket: str = "rfbalance-documents"
    object_storage_access_key: str = ""
    object_storage_secret_key: str = ""
    object_storage_region: str = "us-east-1"
    object_storage_addressing_style: Literal["path", "virtual"] = "path"
