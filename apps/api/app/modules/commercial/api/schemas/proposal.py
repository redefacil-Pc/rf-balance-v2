"""DTOs de proposta (`snake_case`, ADR-0015).

Dinheiro entra como `Decimal` validado e sai como **string decimal**: `float` em
JSON perde centavo em valor grande, e a API financeira não pode depender de como
o cliente parseia número. `customer_document` sai mascarado sem
`proposals:read_pii`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.commercial.application.commands.decide_proposal import Decisao
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import SituacaoDeAprovacao
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta


class ProposalRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    consultant_id: int
    business_date: date
    customer_name: str = Field(min_length=3, max_length=200)
    customer_document: str = Field(min_length=11, max_length=20)
    operation_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    tps_percentage: Decimal = Field(ge=0, le=100, max_digits=9, decimal_places=6)
    #: Redmine/ID externo — único quando informado
    external_id: str | None = Field(default=None, max_length=60)
    bko_collaborator_id: int | None = None
    finalizer_collaborator_id: int | None = None


class UpdateProposalRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    #: versão lida pelo cliente; divergiu, a alteração é recusada com 409
    version: int = Field(ge=1)
    operation_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    tps_percentage: Decimal = Field(ge=0, le=100, max_digits=9, decimal_places=6)
    bko_collaborator_id: int | None = None
    finalizer_collaborator_id: int | None = None


class CancelProposalRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = Field(ge=1)
    #: motivo obrigatório: cancelamento de dado financeiro sempre explica o porquê
    reason: str = Field(min_length=3, max_length=255)


class SubmitProposalRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = Field(ge=1)


class DecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = Field(ge=1)
    decision: Decisao
    #: obrigatório quando `decision` é DEVOLVER; ignorado na aprovação
    reason: str | None = Field(default=None, max_length=255)


class ProposalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    external_id: str | None
    business_date: date
    customer_name: str
    customer_document: str
    consultant_id: int
    consultant_name: str
    bko_collaborator_id: int | None
    finalizer_collaborator_id: int | None
    operation_amount: str
    tps_percentage: str
    company_commission_amount: str
    paid_amount: str
    outstanding_amount: str
    status: StatusDaProposta
    approval_status: SituacaoDeAprovacao
    version: int


class ProposalDetailResponse(ProposalResponse):
    model_config = ConfigDict(frozen=True)

    bko_collaborator_name: str | None
    finalizer_collaborator_name: str | None
    #: recebido acima do excedente tolerado — exige decisão do financeiro
    overpaid: bool
    tolerance_policy_version: str
    rejection_reason: str | None
    submitted_at: datetime | None
    decided_at: datetime | None
    settled_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    timeline: list[ProposalTimelineEventResponse]


class ProposalTimelineEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: str
    occurred_at: datetime
    actor_name: str
    payload: dict[str, object]


class PendingProposalCountResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    count: int


class ProposalWriteResponse(BaseModel):
    """Retorno de escrita: o que mudou de fato, para a tela não recalcular nada."""

    model_config = ConfigDict(frozen=True)

    id: int
    status: StatusDaProposta
    company_commission_amount: str
    outstanding_amount: str
    version: int


class ProposalWithReceiptWriteResponse(ProposalWriteResponse):
    """Criação atômica: identifica também o recebimento persistido."""

    receipt_id: int


class ProposalCancelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    status: StatusDaProposta
    version: int


class ProposalPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[ProposalResponse]
    next_cursor: str | None


class SubmitProposalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    approval_status: SituacaoDeAprovacao
    version: int


class DecisionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    approval_status: SituacaoDeAprovacao
    rejection_reason: str | None
    version: int
