from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CommissionPeriodRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    period_start: date
    period_end: date
    cutoff_at: datetime
    reason: str = Field(min_length=3, max_length=500)


class CommissionPeriodCloseRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reason: str = Field(min_length=3, max_length=500)


class CommissionPeriodResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    period_start: date
    period_end: date
    cutoff_at: datetime
    status: str
    reason: str
    created_at: datetime
    created_by: int
    closed_at: datetime | None
    closed_by: int | None
