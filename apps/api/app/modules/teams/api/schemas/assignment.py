"""DTOs de vínculo consultor-líder."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

TIPOS_DE_VINCULO = "^(COMERCIAL|MEI_GERAL|FINALIZACAO)$"


class AssignLeaderRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    consultant_id: int
    leader_id: int
    assignment_type: str = Field(pattern=TIPOS_DE_VINCULO)
    start_date: date
    #: obrigatório: transferência e correção precisam de motivo auditável (7.3)
    reason: str = Field(min_length=3, max_length=255)


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    consultant_id: int
    leader_id: int
    assignment_type: str
    start_date: date
    end_date: date | None = None
    previous_closed_on: date | None = None


class LeaderAtDateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    assignment_id: int
    leader_id: int
    leader_name: str
    assignment_type: str
    start_date: date
    end_date: date | None


class CloseAssignmentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    end_date: date
    reason: str = Field(min_length=3, max_length=255)
