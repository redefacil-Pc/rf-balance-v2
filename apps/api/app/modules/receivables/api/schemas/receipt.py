from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ReceiptDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ReceiptDecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    decision: ReceiptDecision
    reason: str | None = Field(default=None, max_length=255)


class ReceiptReversalRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reason: str = Field(min_length=3, max_length=255)
    business_date: date
    amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    proposal_id: int
    proposal_approval_status: str
    customer_name: str
    amount: str
    business_date: date
    payment_datetime: datetime | None
    payment_method: str
    reference: str | None
    notes: str | None
    status: str
    rejection_reason: str | None
    proof_file_name: str
    created_at: datetime
    created_by: int
    creator_name: str
    decided_at: datetime | None
    decided_by: int | None
    reversed: bool
    reversed_amount: str
    net_amount: str
    reversal_reason: str | None


class ReceiptPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[ReceiptResponse]


class ReceiptWriteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    proposal_id: int
    status: str
    amount: str
    proposal_status: str
    proposal_paid_amount: str
    proposal_outstanding_amount: str
