from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BeneficiaryPolicyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    collaborator_id: int = Field(gt=0)
    valid_from: date
    excluded: bool = False
    override_tps_35_percentage: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=6)
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def compatible(self) -> BeneficiaryPolicyRequest:
        if self.excluded and self.override_tps_35_percentage is not None:
            raise ValueError("Exclusão total não pode ter override.")
        return self


class BeneficiaryPolicyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    collaborator_id: int
    collaborator_name: str
    valid_from: date
    valid_to: date | None
    excluded: bool
    override_tps_35_percentage: str | None
    reason: str
