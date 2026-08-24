"""Agregador de configuração, com validação fail-fast no startup."""

from dataclasses import dataclass
from functools import lru_cache

from app.platform.config.app import AppSettings
from app.platform.config.database import DatabaseSettings
from app.platform.config.pii import PiiSettings
from app.platform.config.redis import RedisSettings
from app.platform.config.retention import RetentionSettings
from app.platform.config.security import SecuritySettings
from app.platform.config.storage import StorageSettings


@dataclass(frozen=True, slots=True)
class Settings:
    app: AppSettings
    database: DatabaseSettings
    redis: RedisSettings
    storage: StorageSettings
    security: SecuritySettings
    pii: PiiSettings
    retention: RetentionSettings

    def validar(self) -> None:
        """Levanta erro antes de a aplicação aceitar tráfego."""
        self.security.validar_para_ambiente()
        self.pii.validar_para_ambiente()
        if self.app.is_production and not self.app.cors_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS é obrigatório em produção")
        if self.app.is_production and not self.app.metrics_token:
            raise ValueError("METRICS_TOKEN é obrigatório em produção")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app=AppSettings(),
        database=DatabaseSettings(),
        redis=RedisSettings(),
        storage=StorageSettings(),
        security=SecuritySettings(),
        pii=PiiSettings(),
        retention=RetentionSettings(),
    )
