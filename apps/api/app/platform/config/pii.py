"""Configuração das chaves de PII (ADR-0012).

Distintas do `SECRET_KEY`: rotação de sessão e rotação de PII têm ciclos
diferentes. Trocar o pepper invalida todos os hashes de busca.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

# Usadas apenas em `local` e `test`, para o ambiente subir sem configuração
# manual. Fora desses ambientes, `validar_para_ambiente` exige as reais.
# base64 de 'local-dev-pii-key-32-bytes-only!' — exatamente 32 bytes.
CHAVE_DE_DESENVOLVIMENTO = "bG9jYWwtZGV2LXBpaS1rZXktMzItYnl0ZXMtb25seSE="
PEPPER_DE_DESENVOLVIMENTO = "local-dev-pepper-nao-usar-fora-de-local"


class PiiSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    pii_encryption_key: str = ""
    pii_hash_pepper: str = ""
    app_env: str = "local"

    @property
    def chave(self) -> str:
        return self.pii_encryption_key or CHAVE_DE_DESENVOLVIMENTO

    @property
    def pepper(self) -> str:
        return self.pii_hash_pepper or PEPPER_DE_DESENVOLVIMENTO

    def validar_para_ambiente(self) -> None:
        if self.app_env in {"local", "test"}:
            return
        if not self.pii_encryption_key:
            raise ValueError(f"PII_ENCRYPTION_KEY é obrigatória em APP_ENV={self.app_env}")
        if not self.pii_hash_pepper:
            raise ValueError(f"PII_HASH_PEPPER é obrigatório em APP_ENV={self.app_env}")
