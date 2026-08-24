"""Caso de uso: cadastrar proposta (seção 7.4).

Um único commit cobre proposta e auditoria. O documento do cliente é normalizado
e validado aqui — proposta com CPF inválido é retrabalho manual na conciliação —
e vai para o banco cifrado, com hash para busca (ADR-0012).

O pagamento inicial opcional da seção 7.4 **não** entra aqui: recebimento é
registro em `receipts`, tabela do módulo `receivables` (F3), com idempotência
própria. A proposta nasce `OPEN` e o primeiro recebimento a move de estado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.commercial.domain.entities.proposal import Proposal
from app.modules.commercial.domain.errors import (
    DocumentoDoClienteInvalidoError,
    ExternalIdDuplicadoError,
    ParticipanteInvalidoError,
    TpsInvalidoError,
    ValorDaOperacaoInvalidoError,
)
from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security.pii_cipher import PiiCipher
from app.shared.domain.dinheiro import Dinheiro
from app.shared.domain.documento import Documento

MODULO = "commercial"


@dataclass(frozen=True, slots=True)
class CreateProposal:
    consultant_id: int
    business_date: date
    customer_name: str
    customer_document: str
    operation_amount: Decimal
    tps_percentage: Decimal
    external_id: str | None = None
    bko_collaborator_id: int | None = None
    finalizer_collaborator_id: int | None = None
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class PropostaCriada:
    id: int
    status: str
    company_commission_amount: Dinheiro
    outstanding_amount: Dinheiro
    version: int


class CreateProposalHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        propostas: SqlProposalRepository,
        colaboradores: SqlCollaboratorRepository,
        cipher: PiiCipher,
        audit: AuditRecorder,
    ) -> None:
        self._uow = uow
        self._propostas = propostas
        self._colaboradores = colaboradores
        self._cipher = cipher
        self._audit = audit

    async def execute(self, cmd: CreateProposal, *, commit: bool = True) -> PropostaCriada:
        documento = self._normalizar_documento(cmd.customer_document)
        await self._validar_participantes(cmd)
        await self._validar_external_id(cmd.external_id)

        proposta = Proposal(
            consultant_id=cmd.consultant_id,
            business_date=cmd.business_date,
            customer_name=cmd.customer_name,
            customer_document=documento,
            operation_amount=self._valor(cmd.operation_amount),
            tps=self._tps(cmd.tps_percentage),
            external_id=cmd.external_id,
            bko_collaborator_id=cmd.bko_collaborator_id,
            finalizer_collaborator_id=cmd.finalizer_collaborator_id,
        )

        await self._propostas.criar(
            proposta,
            document_hash=self._cipher.hash_de_busca(documento.digitos),
            ator=cmd.ator,
        )
        assert proposta.id is not None

        self._audit.registrar(
            module=MODULO,
            action="proposal.created",
            actor_user_id=cmd.ator,
            aggregate_type="proposal",
            aggregate_id=str(proposta.id),
            correlation_id=cmd.correlation_id,
            payload={
                "external_id": cmd.external_id,
                "consultant_id": cmd.consultant_id,
                "business_date": cmd.business_date.isoformat(),
                "operation_amount": str(proposta.operation_amount),
                "tps_percentage": str(proposta.tps),
                "company_commission_amount": str(proposta.company_commission_amount),
                # nome do cliente é PII: vai o hash do documento, não o dado
                "customer_document_hash": self._cipher.hash_de_busca(documento.digitos),
            },
        )
        if commit:
            await self._uow.commit()

        return PropostaCriada(
            id=proposta.id,
            status=proposta.status.value,
            company_commission_amount=proposta.company_commission_amount,
            outstanding_amount=proposta.outstanding_amount,
            version=proposta.version,
        )

    @staticmethod
    def _normalizar_documento(bruto: str) -> Documento:
        try:
            return Documento.normalizar(bruto)
        except ValueError as exc:
            raise DocumentoDoClienteInvalidoError(str(exc)) from exc

    @staticmethod
    def _valor(bruto: Decimal) -> Dinheiro:
        try:
            return Dinheiro.de(bruto)
        except ValueError as exc:
            raise ValorDaOperacaoInvalidoError(str(exc)) from exc

    @staticmethod
    def _tps(bruto: Decimal) -> PercentualTps:
        try:
            return PercentualTps.de(bruto)
        except ValueError as exc:
            raise TpsInvalidoError(str(exc)) from exc

    async def _validar_external_id(self, external_id: str | None) -> None:
        if external_id and await self._propostas.existe_external_id(external_id):
            raise ExternalIdDuplicadoError(external_id)

    async def _validar_participantes(self, cmd: CreateProposal) -> None:
        consultor = await self._colaboradores.buscar_por_id(cmd.consultant_id)
        if consultor is None:
            raise ParticipanteInvalidoError("Consultor não encontrado.")
        if not consultor.is_active:
            raise ParticipanteInvalidoError("O consultor está inativo e não pode receber proposta.")

        papeis_do_consultor = {
            item.role
            for item in await self._colaboradores.papeis_vigentes_em(
                cmd.consultant_id, cmd.business_date
            )
        }
        papeis_de_lideranca = {"LIDER", "LIDER_MEI_GERAL", "LIDER_FINALIZACAO"}
        if papeis_do_consultor & papeis_de_lideranca:
            raise ParticipanteInvalidoError(
                "Liderança não realiza venda e não pode ser indicada como consultor da proposta."
            )
        if not papeis_do_consultor.intersection({"CONSULTOR", "CONSULTOR_MEI_ESCALONADO"}):
            raise ParticipanteInvalidoError(
                "O colaborador não possui função de consultor vigente na data do negócio."
            )

        for rotulo, papel, colaborador_id in (
            ("BKO", "BKO", cmd.bko_collaborator_id),
            ("finalização", "FINALIZACAO", cmd.finalizer_collaborator_id),
        ):
            if colaborador_id is None:
                continue
            colaborador = await self._colaboradores.buscar_por_id(colaborador_id)
            if colaborador is None or not colaborador.is_active:
                raise ParticipanteInvalidoError(
                    f"Colaborador de {rotulo} não encontrado ou inativo."
                )
            papeis = await self._colaboradores.papeis_vigentes_em(colaborador_id, cmd.business_date)
            if not any(item.role == papel for item in papeis):
                raise ParticipanteInvalidoError(
                    f"O colaborador não possui função de {rotulo} vigente na data do negócio."
                )
