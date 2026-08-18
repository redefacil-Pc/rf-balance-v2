from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    occurred_at: datetime
    business_date: date
    module: str
    action: str
    actor_user_id: int | None
    actor_name: str
    aggregate_type: str | None
    aggregate_id: str | None
    correlation_id: str | None
    payload: dict[str, Any]


class AuditEventPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[AuditEventResponse]
    next_cursor: str | None


class AuditOptionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    modules: list[str]
    actions: list[str]
    aggregate_types: list[str]
