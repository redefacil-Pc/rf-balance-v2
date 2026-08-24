"""Configuração geral da aplicação."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    app_env: Environment = "local"
    app_timezone: str = "America/Sao_Paulo"
    log_level: str = "INFO"
    cors_allowed_origins: str = ""
    # Token dedicado ao scraper. Em producao, /metrics nunca fica anonimo.
    metrics_token: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins(self) -> list[str]:
        """Allowlist exata de origens; vazia significa nenhuma origem cruzada."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
