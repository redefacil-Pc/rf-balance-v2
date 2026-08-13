"""DTOs de empresa e unidade (`snake_case`, ADR-0015)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CompanyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    legal_name: str = Field(min_length=2, max_length=200)
    trade_name: str = Field(default="", max_length=200)
    #: CNPJ; aceita com ou sem máscara, normalizado no domínio
    document: str | None = Field(default=None, max_length=20)


class CompanyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    legal_name: str
    trade_name: str
    is_active: bool


class UnitRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: int
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=120)


class UnitResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    company_id: int
    code: str
    name: str
    is_active: bool
