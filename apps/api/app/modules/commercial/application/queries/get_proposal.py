"""Query: detalhe de uma proposta (seção 7.4).

Devolve os mesmos números da listagem, acrescidos do que só interessa na tela de
detalhe: carimbos de quitação e cancelamento, política de tolerância aplicada e
sinalização de sobrepagamento — o excedente acima do tolerado precisa aparecer
para alguém decidir o que fazer, não ficar escondido num total.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.modules.audit.application.queries.list_audit_events import (
    AuditFilters,
    ListAuditEventsQuery,
)
from app.modules.commercial.application.ports.proposal_scope import EscopoDePropostas
from app.modules.commercial.domain.errors import PropostaNaoEncontradaError
from app.modules.commercial.domain.policies import settlement_tolerance_policy as tolerancia
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
    ids_de_colaboradores,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.security.pii_cipher import PiiCipher
from app.shared.domain.dinheiro import Dinheiro
from app.shared.domain.documento import Documento, TipoDeDocumento


@dataclass(frozen=True, slots=True)
class DetalheDaProposta:
    id: int
    external_id: str | None
    business_date: date
    customer_name: str
    customer_document: str
    consultant_id: int
    consultant_name: str
    bko_collaborator_id: int | None
    bko_collaborator_name: str | None
    finalizer_collaborator_id: int | None
    finalizer_collaborator_name: str | None
    operation_amount: str
    tps_percentage: str
    company_commission_amount: str
    paid_amount: str
    outstanding_amount: str
    status: str
    approval_status: str
    rejection_reason: str | None
    submitted_at: datetime | None
    decided_at: datetime | None
    overpaid: bool
    tolerance_policy_version: str
    settled_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    timeline: tuple[EventoDaProposta, ...]
    version: int


@dataclass(frozen=True, slots=True)
class EventoDaProposta:
    action: str
    occurred_at: datetime
    actor_name: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class GetProposal:
    proposal_id: int
    pode_ver_pii: bool
    #: recorte de leitura; fora dele a proposta responde 404, não 403 — um 403
    #: confirmaria que ela existe
    escopo: EscopoDePropostas | None = None


class GetProposalHandler:
    def __init__(
        self,
        *,
        propostas: SqlProposalRepository,
        colaboradores: SqlCollaboratorRepository,
        cipher: PiiCipher,
        audit: ListAuditEventsQuery,
    ) -> None:
        self._propostas = propostas
        self._colaboradores = colaboradores
        self._cipher = cipher
        self._audit = audit

    async def execute(self, query: GetProposal) -> DetalheDaProposta:
        modelo = await self._propostas.obter_linha(query.proposal_id, escopo=query.escopo)
        if modelo is None:
            raise PropostaNaoEncontradaError(f"Proposta {query.proposal_id} não encontrada.")

        nomes = await self._colaboradores.nomes_por_id(
            tuple(sorted(ids_de_colaboradores([modelo])))
        )
        eventos = await self._audit.execute(
            filters=AuditFilters(
                module="commercial",
                action="proposal.",
                aggregate_type="proposal",
                aggregate_id=str(modelo.id),
            ),
            limit=100,
            cursor=None,
        )

        return DetalheDaProposta(
            id=modelo.id,
            external_id=modelo.external_id,
            business_date=modelo.business_date,
            customer_name=modelo.customer_name,
            customer_document=self._documento(modelo, query.pode_ver_pii),
            consultant_id=modelo.consultant_id,
            consultant_name=nomes.get(modelo.consultant_id, ""),
            bko_collaborator_id=modelo.bko_collaborator_id,
            bko_collaborator_name=self._nome(nomes, modelo.bko_collaborator_id),
            finalizer_collaborator_id=modelo.finalizer_collaborator_id,
            finalizer_collaborator_name=self._nome(nomes, modelo.finalizer_collaborator_id),
            operation_amount=f"{modelo.operation_amount:.2f}",
            tps_percentage=f"{modelo.tps_percentage:.6f}",
            company_commission_amount=f"{modelo.company_commission_amount:.2f}",
            paid_amount=f"{modelo.paid_amount_cached:.2f}",
            outstanding_amount=f"{modelo.outstanding_amount_cached:.2f}",
            status=modelo.status,
            approval_status=modelo.approval_status,
            rejection_reason=modelo.rejection_reason,
            submitted_at=modelo.submitted_at,
            decided_at=modelo.decided_at,
            overpaid=self._sobrepago(modelo),
            tolerance_policy_version=modelo.tolerance_policy_version,
            settled_at=modelo.settled_at,
            cancelled_at=modelo.cancelled_at,
            cancellation_reason=modelo.cancellation_reason,
            timeline=tuple(
                EventoDaProposta(
                    action=evento.action,
                    occurred_at=evento.occurred_at,
                    actor_name=evento.actor_name,
                    payload=evento.payload,
                )
                for evento in reversed(eventos.itens)
            ),
            version=modelo.version,
        )

    @staticmethod
    def _sobrepago(modelo: ProposalModel) -> bool:
        politica = tolerancia.resolver(modelo.tolerance_policy_version)
        resultado = politica.classificar(
            esperado=Dinheiro(modelo.company_commission_amount),
            recebido=Dinheiro(modelo.paid_amount_cached),
        )
        return resultado is tolerancia.ResultadoDeQuitacao.SOBREPAGAMENTO

    @staticmethod
    def _nome(nomes: dict[int, str], colaborador_id: int | None) -> str | None:
        return None if colaborador_id is None else nomes.get(colaborador_id, "")

    def _documento(self, modelo: ProposalModel, pode_ver_pii: bool) -> str:
        documento = Documento(
            self._cipher.decifrar(modelo.customer_document_encrypted),
            TipoDeDocumento(modelo.customer_document_type),
        )
        return documento.formatado() if pode_ver_pii else documento.mascarado()
