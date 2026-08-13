"""Configuração de segredos, sessão e rate limit de login.

O transporte da sessão é cookie HttpOnly com token opaco (ADR-0003). Não há JWT.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSEGUROS = {"", "changeme", "troque-em-local", "troque-em-local-gerar-com-openssl-rand-hex-32"}

SESSION_COOKIE = "rfb_session"
CSRF_COOKIE = "rfb_csrf"
CSRF_HEADER = "X-CSRF-Token"


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    secret_key: str = ""
    app_env: str = "local"

    # sessão
    session_ttl: int = Field(default=1_209_600, ge=300)
    session_rotation_interval: int = Field(default=900, ge=60)
    session_cache_ttl: int = Field(default=60, ge=0, le=300)
    cookie_secure: bool = False
    cookie_domain: str = ""

    # rate limit do login
    login_max_attempts: int = Field(default=5, ge=1)
    login_attempt_window: int = Field(default=900, ge=60)

    @field_validator("secret_key")
    @classmethod
    def _tamanho_minimo(cls, valor: str) -> str:
        if valor in _INSEGUROS:
            return valor  # validado contra o ambiente em validar_para_ambiente
        if len(valor) < 32:
            raise ValueError("SECRET_KEY deve ter ao menos 32 caracteres")
        return valor

    def validar_para_ambiente(self) -> None:
        """Fail-fast: configuração de local nunca sobe para outro ambiente."""
        if self.app_env == "local":
            return
        if self.secret_key in _INSEGUROS:
            raise ValueError(f"SECRET_KEY inválida para APP_ENV={self.app_env}")
        if not self.cookie_secure:
            raise ValueError(f"COOKIE_SECURE deve ser true em APP_ENV={self.app_env}")
