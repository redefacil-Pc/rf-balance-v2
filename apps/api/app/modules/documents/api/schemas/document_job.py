from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator


class CreateDocumentJobRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    period_start: date
    period_end: date
    unit_id: int | None = None
    leader_id: int | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "CreateDocumentJobRequest":
        if self.period_end < self.period_start:
            raise ValueError("O fim do período deve ser posterior ao início.")
        if (self.period_end - self.period_start).days > 92:
            raise ValueError("O período não pode ultrapassar 93 dias.")
        if self.unit_id is not None and self.leader_id is not None:
            raise ValueError("Selecione apenas um recorte: unidade ou equipe.")
        return self


class DocumentJobResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    job_type: str
    status: str
    period_start: date
    period_end: date
    unit_id: int | None
    leader_id: int | None
    total_items: int
    processed_items: int
    attempt_count: int
    max_attempts: int
    error_message: str | None
    archive_ready: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class DocumentJobPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[DocumentJobResponse]
