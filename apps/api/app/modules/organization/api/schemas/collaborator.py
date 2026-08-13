"""DTOs de colaborador (`snake_case`, ADR-0015).

O campo `document` na resposta vem **mascarado** quando quem consulta não tem
`collaborators:read_pii`.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.modules.organization.domain.value_objects.papel_de_colaborador import (
    PapelDeColaborador,
    RegimeTributario,
)


class RoleRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: PapelDeColaborador
    valid_from: date
    valid_to: date | None = None


class PaymentKeyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key_type: str = Field(pattern="^(CPF|CNPJ|EMAIL|TELEFONE|ALEATORIA)$")
    key: str = Field(min_length=3, max_length=140)


class CollaboratorRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: int
    unit_id: int | None = None
    full_name: str = Field(min_length=3, max_length=200)
    document: str = Field(min_length=11, max_length=20)
    tax_regime: RegimeTributario
    roles: list[RoleRequest] = Field(min_length=1)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    payment_key: PaymentKeyRequest | None = None
    #: conta de acesso existente, vinculada no mesmo commit. Nulo para quem não
    #: usa o sistema — o BKO, por exemplo, é só cadastro.
    user_id: int | None = None


class CollaboratorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    full_name: str
    company_id: int
    unit_id: int | None
    tax_regime: str
    is_active: bool
    roles: list[str]
    document: str
    document_type: str
    #: conta de acesso vinculada; nulo para quem não usa o sistema
    user_id: int | None = None


class DeactivateCollaboratorRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    deactivated_on: date
    #: motivo é obrigatório (seção 7.2) e vai para a auditoria
    reason: str = Field(min_length=3, max_length=255)


class UpdateCollaboratorRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: int
    unit_id: int | None = None
    full_name: str = Field(min_length=3, max_length=200)
    tax_regime: RegimeTributario


class CollaboratorPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[CollaboratorResponse]
    next_cursor: str | None


class LinkAccountRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    #: nulo desfaz o vínculo — a pessoa continua cadastrada, sem acesso
    user_id: int | None


class AddFunctionRequest(BaseModel):
    """Abre uma função. Trocar de função é encerrar a atual e abrir esta."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    function: PapelDeColaborador
    valid_from: date
    #: normalmente nulo: função nasce sem fim previsto
    valid_to: date | None = None


class CloseFunctionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    valid_to: date


class FunctionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    role: PapelDeColaborador
    valid_from: date
    valid_to: date | None
    current: bool
