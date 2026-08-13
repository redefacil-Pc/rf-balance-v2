"""DTOs de comprovante de proposta (`snake_case`, ADR-0015)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime
    uploaded_by: int | None


class AttachmentUploadResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
