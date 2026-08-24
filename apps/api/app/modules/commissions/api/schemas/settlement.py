from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BkoManualEntryRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    beneficiary_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    effective_date: date
    description: str = Field(min_length=3, max_length=255)


class BkoManualEntryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    beneficiary_id: int
    amount: str
    effective_date: date
    description: str


class FinalizationManualEntryRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    beneficiary_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    effective_date: date
    description: str = Field(min_length=3, max_length=255)


class FinalizationManualEntryResponse(BkoManualEntryResponse):
    pass


class SettlementPeriodRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    period_start: date
    period_end: date


class SettlementAdjustmentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    bonus_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    deferred_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    notes: str | None = Field(default=None, max_length=255)


class SettlementPaymentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_date: date
    payment_method: str = Field(min_length=2, max_length=30)
    reference: str | None = Field(default=None, max_length=100)


class SettlementResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    beneficiary_id: int
    beneficiary_name: str
    roles: list[str]
    period_start: date
    period_end: date
    gross_amount: str
    carryover_amount: str
    bonus_amount: str
    discount_amount: str
    manual_discount_amount: str
    reversal_discount_amount: str
    reversal_carryover_amount: str
    deferred_amount: str
    paid_amount: str
    payable_amount: str
    status: str
    payment_date: date | None
    payment_method: str | None
    payment_reference: str | None
    notes: str | None
    created_at: datetime


class SettlementPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[SettlementResponse]
