from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetentionSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    integrity_retention_days: int = Field(default=30, ge=1, le=3650)
    outbox_retention_days: int = Field(default=30, ge=1, le=3650)
    generated_document_retention_days: int = Field(default=90, ge=1, le=3650)
    orphan_storage_grace_hours: int = Field(default=24, ge=1, le=720)
    redis_stream_maxlen: int = Field(default=10_000, ge=100, le=10_000_000)
    retention_cleanup_hour_utc: int = Field(default=4, ge=0, le=23)
