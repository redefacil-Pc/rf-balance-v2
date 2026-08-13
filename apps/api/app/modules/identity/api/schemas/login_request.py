"""DTO de entrada do login."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    # o tamanho mínimo real é validado pela política de senha no domínio;
    # aqui só evitamos processar payload vazio
    password: str = Field(min_length=1, max_length=128)
