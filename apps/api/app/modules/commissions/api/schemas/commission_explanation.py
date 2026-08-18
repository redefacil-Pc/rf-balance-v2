from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CommissionEntryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    entry_type: str
    amount: str
    competence_date: date
    description: str
    reversal_id: int | None
    created_at: datetime


class CommissionCalculationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    proposal_id: int
    receipt_id: int
    beneficiary_id: int
    beneficiary_name: str
    strategy: str
    rule_version: str | None
    competence_date: date
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    calculated_at: datetime
    entries: list[CommissionEntryResponse]
    net_amount: str


class CommissionExplanationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[CommissionCalculationResponse]
    total_net_amount: str
