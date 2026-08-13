"""Configuração de acesso ao banco de dados."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    database_url: str = "mysql+asyncmy://rfbalance:rfbalance@db:3306/rfbalance"
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=5, ge=0, le=100)
    database_pool_recycle: int = Field(default=1800, ge=60)
    database_echo: bool = False

    # conta com privilégio de DDL, usada apenas pelo Alembic
    migration_database_url: str | None = None

    @property
    def migration_url(self) -> str:
        return self.migration_database_url or self.database_url
