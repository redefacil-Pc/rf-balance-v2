from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReceivingAccountRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    #: rótulo livre, como no v1: "Almeida Serviços LTDA (SANTANDER)"
    label: str = Field(min_length=3, max_length=160)
    #: ausente no cadastro coloca a conta no fim da lista
    display_order: int | None = Field(default=None, ge=0, le=9999)


class ReceivingAccountStatusRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    is_active: bool


class ReceivingAccountResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    label: str
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
