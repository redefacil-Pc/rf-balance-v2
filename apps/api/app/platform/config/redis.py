"""Configuração do Redis (fila, cache e locks curtos)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    redis_url: str = "redis://redis:6379/0"
