from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommissionBandInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tax_regime: str = Field(pattern="^MEI$")
    tps_min: Decimal = Field(ge=0, le=100, max_digits=9, decimal_places=6)
    tps_max: Decimal | None = Field(default=None, gt=0, le=100, max_digits=9, decimal_places=6)
    percentage: Decimal = Field(ge=0, le=100, max_digits=9, decimal_places=6)


class CreateCommissionRuleSetRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=3, max_length=120)
    valid_from: date
    reason: str = Field(min_length=3, max_length=500)
    rules: list[CommissionBandInput] = Field(min_length=2, max_length=40)

    @model_validator(mode="after")
    def regimes_obrigatorios(self) -> CreateCommissionRuleSetRequest:
        if {regra.tax_regime for regra in self.rules} != {"MEI"}:
            raise ValueError("Informe as faixas completas do consultor MEI.")
        return self


class ActivateCommissionRuleSetRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reason: str = Field(min_length=3, max_length=500)


class CommissionBandResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    tax_regime: str
    tps_min: str
    tps_max: str | None
    percentage: str
    sort_order: int


class CommissionRuleSetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    strategy: str
    version: str
    name: str
    status: str
    valid_from: date
    valid_to: date | None
    reason: str
    created_at: datetime
    created_by: int | None
    activated_at: datetime | None
    activated_by: int | None
    rules: list[CommissionBandResponse]


class CreateStrategyConfigRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    strategy: str = Field(
        pattern="^(SCALED_CONSULTANT|COMMERCIAL_LEADER|GENERAL_MEI_LEADER|FINALIZER|FINALIZATION_LEADER)$"
    )
    version: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=3, max_length=120)
    valid_from: date
    reason: str = Field(min_length=3, max_length=500)
    config: dict[str, Any]


class StrategyConfigResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    strategy: str
    version: str
    name: str
    status: str
    valid_from: date
    valid_to: date | None
    config: dict[str, Any]
    reason: str
    created_at: datetime
    created_by: int | None
    activated_at: datetime | None
    activated_by: int | None
