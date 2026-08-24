"""Persistência do aggregate `Proposal`.

Escrita carrega a linha com `SELECT ... FOR UPDATE` e confere a `version` que o
cliente enviou: o lock serializa gravações concorrentes no banco, e a `version`
impede que uma tela aberta há dez minutos sobrescreva o que outra pessoa já
alterou (seção 7.4).

A listagem devolve linhas, não entidades: é caminho de leitura (CQRS leve) e não
precisa reconstruir domínio para desenhar uma tabela.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import ColumnElement, Select, and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commercial.application.ports.proposal_scope import EscopoDePropostas
from app.modules.commercial.domain.entities.proposal import Proposal
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import SituacaoDeAprovacao
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.modules.commercial.infrastructure.mappers import proposal_mapper
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.platform.errors.domain_error import ConcurrencyConflictError
from app.platform.http.pagination import Cursor
from app.platform.security.pii_cipher import PiiCipher


@dataclass(frozen=True, slots=True)
class FiltroDePropostas:
    """Filtros da listagem da seção 7.4."""

    status: str | None = None
    #: fila do financeiro: SUBMITTED lista o que aguarda decisão
    approval_status: str | None = None
    #: listagem operacional: o que está na fila do Financeiro fica fora dela
    exclude_approval_status: str | None = None
    consultant_id: int | None = None
    bko_collaborator_id: int | None = None
    finalizer_collaborator_id: int | None = None
    de: date | None = None
    ate: date | None = None
    external_id: str | None = None
    #: busca exata por documento do cliente, pelo hash (ADR-0012)
    customer_document_hash: str | None = None
    busca_por_cliente: str | None = None
    #: recorte de "o que é meu" (ver `ProposalScopeResolver`). `None` só quando
    #: quem consulta lê a base inteira — nunca por omissão de quem chama.
    escopo: EscopoDePropostas | None = None


class SqlProposalRepository:
    __slots__ = ("_cipher", "_session")

    def __init__(self, session: AsyncSession, cipher: PiiCipher) -> None:
        self._session = session
        self._cipher = cipher

    async def criar(
        self,
        proposta: Proposal,
        *,
        document_hash: str,
        ator: int | None,
    ) -> Proposal:
        modelo = ProposalModel(
            external_id=proposta.external_id,
            consultant_id=proposta.consultant_id,
            bko_collaborator_id=proposta.bko_collaborator_id,
            finalizer_collaborator_id=proposta.finalizer_collaborator_id,
            business_date=proposta.business_date,
            customer_name=proposta.customer_name,
            customer_document_encrypted=self._cipher.cifrar(proposta.customer_document.digitos),
            customer_document_hash=document_hash,
            customer_document_type=proposta.customer_document.tipo.value,
            operation_amount=proposta.operation_amount.valor,
            tps_percentage=proposta.tps.valor,
            company_commission_amount=proposta.company_commission_amount.valor,
            paid_amount_cached=proposta.paid_amount.valor,
            outstanding_amount_cached=proposta.outstanding_amount.valor,
            status=proposta.status.value,
            approval_status=proposta.approval_status.value,
            rejection_reason=proposta.rejection_reason,
            tolerance_policy_version=proposta.tolerance_policy_version,
            created_by=ator,
            updated_by=ator,
        )
        self._session.add(modelo)
        await self._session.flush()
        proposta.id = modelo.id
        return proposta

    async def obter_linha(
        self, proposal_id: int, *, escopo: EscopoDePropostas | None = None
    ) -> ProposalModel | None:
        """Leitura de tela: a linha basta, sem reconstruir o aggregate.

        O escopo entra na **query**, não numa checagem depois: fora do recorte a
        proposta simplesmente não existe para quem perguntou, e quem chama
        devolve 404. Um 403 já confirmaria que ela existe.
        """
        consulta = select(ProposalModel).where(ProposalModel.id == proposal_id)
        if escopo is not None and not escopo.irrestrito:
            consulta = consulta.where(condicao_de_escopo(escopo))
        encontrada: ProposalModel | None = await self._session.scalar(consulta)
        return encontrada

    async def obter(self, proposal_id: int) -> Proposal | None:
        modelo = await self._linha(proposal_id)
        return None if modelo is None else proposal_mapper.para_entidade(modelo, self._cipher)

    async def obter_para_atualizacao(self, proposal_id: int) -> Proposal | None:
        modelo = await self._linha(proposal_id, para_atualizacao=True)
        return None if modelo is None else proposal_mapper.para_entidade(modelo, self._cipher)

    async def salvar(
        self,
        proposta: Proposal,
        *,
        versao_do_cliente: int,
        quando: datetime,
        ator: int | None,
        motivo_do_cancelamento: str | None = None,
    ) -> None:
        if proposta.id is None:
            raise ValueError("proposta sem id não pode ser salva")

        modelo = await self._linha(proposta.id, para_atualizacao=True)
        if modelo is None:
            raise ValueError(f"proposta {proposta.id} desapareceu entre a leitura e a escrita")
        if modelo.version != versao_do_cliente:
            raise ConcurrencyConflictError(
                "A proposta foi alterada desde que você a carregou. "
                "Recarregue e refaça a alteração."
            )

        # carimbos do fluxo de aprovação, antes de o mapper igualar os campos
        aprovacao_mudou = modelo.approval_status != proposta.approval_status.value
        if aprovacao_mudou and proposta.approval_status is SituacaoDeAprovacao.SUBMITTED:
            modelo.submitted_at = quando
            modelo.submitted_by = ator
        elif aprovacao_mudou:
            modelo.decided_at = quando
            modelo.decided_by = ator

        proposal_mapper.aplicar_na_linha(modelo, proposta)
        modelo.updated_by = ator
        modelo.version = modelo.version + 1

        if proposta.status is StatusDaProposta.PAID and modelo.settled_at is None:
            modelo.settled_at = quando
        elif proposta.status is not StatusDaProposta.PAID:
            # estorno reabre a proposta: a data de quitação deixa de valer
            modelo.settled_at = None

        if proposta.status is StatusDaProposta.CANCELLED:
            modelo.cancelled_at = quando
            modelo.cancellation_reason = motivo_do_cancelamento

        await self._session.flush()
        proposta.version = modelo.version

    async def existe_external_id(self, external_id: str) -> bool:
        encontrado = await self._session.scalar(
            select(ProposalModel.id).where(ProposalModel.external_id == external_id)
        )
        return encontrado is not None

    async def listar(
        self,
        *,
        filtro: FiltroDePropostas,
        limite: int,
        cursor: Cursor | None,
    ) -> tuple[list[ProposalModel], bool]:
        """Ordena por (business_date desc, id desc): a proposta nova vem primeiro,
        e o par sustenta o cursor sem `OFFSET`."""
        consulta = self._aplicar_filtros(select(ProposalModel), filtro)

        if cursor is not None:
            chave = date.fromisoformat(cursor.chave)
            consulta = consulta.where(
                or_(
                    ProposalModel.business_date < chave,
                    and_(ProposalModel.business_date == chave, ProposalModel.id < cursor.id),
                )
            )

        consulta = consulta.order_by(
            ProposalModel.business_date.desc(), ProposalModel.id.desc()
        ).limit(limite + 1)
        encontradas = list((await self._session.scalars(consulta)).all())

        return encontradas[:limite], len(encontradas) > limite

    async def contar(self, filtro: FiltroDePropostas) -> int:
        consulta = self._aplicar_filtros(select(ProposalModel), filtro)
        subconsulta = consulta.with_only_columns(ProposalModel.id).subquery()
        return int(await self._session.scalar(select(func.count()).select_from(subconsulta)) or 0)

    async def _linha(
        self, proposal_id: int, *, para_atualizacao: bool = False
    ) -> ProposalModel | None:
        consulta = select(ProposalModel).where(ProposalModel.id == proposal_id)
        if para_atualizacao:
            consulta = consulta.with_for_update()
        encontrada: ProposalModel | None = await self._session.scalar(consulta)
        return encontrada

    @staticmethod
    def _aplicar_filtros(
        consulta: Select[tuple[ProposalModel]], filtro: FiltroDePropostas
    ) -> Select[tuple[ProposalModel]]:
        if filtro.status is not None:
            consulta = consulta.where(ProposalModel.status == filtro.status)
        if filtro.approval_status is not None:
            consulta = consulta.where(ProposalModel.approval_status == filtro.approval_status)
        if filtro.exclude_approval_status is not None:
            consulta = consulta.where(
                ProposalModel.approval_status != filtro.exclude_approval_status
            )
        if filtro.consultant_id is not None:
            consulta = consulta.where(ProposalModel.consultant_id == filtro.consultant_id)
        if filtro.bko_collaborator_id is not None:
            consulta = consulta.where(
                ProposalModel.bko_collaborator_id == filtro.bko_collaborator_id
            )
        if filtro.finalizer_collaborator_id is not None:
            consulta = consulta.where(
                ProposalModel.finalizer_collaborator_id == filtro.finalizer_collaborator_id
            )
        if filtro.de is not None:
            consulta = consulta.where(ProposalModel.business_date >= filtro.de)
        if filtro.ate is not None:
            consulta = consulta.where(ProposalModel.business_date <= filtro.ate)
        if filtro.external_id is not None:
            consulta = consulta.where(ProposalModel.external_id == filtro.external_id)
        if filtro.customer_document_hash is not None:
            consulta = consulta.where(
                ProposalModel.customer_document_hash == filtro.customer_document_hash
            )
        if filtro.busca_por_cliente:
            # prefixo usa índice; `%termo%` faria varredura na tabela inteira
            consulta = consulta.where(
                ProposalModel.customer_name.like(f"{filtro.busca_por_cliente}%")
            )
        if filtro.escopo is not None and not filtro.escopo.irrestrito:
            # escopo do RBAC aplicado em SQL, nunca filtrado no cliente
            consulta = consulta.where(condicao_de_escopo(filtro.escopo))
        return consulta


def condicao_de_escopo(escopo: EscopoDePropostas) -> ColumnElement[bool]:
    """Traduz o escopo em SQL.

    Participação cobre as **três** colunas: uma pessoa de finalização não entra
    na proposta como consultor, e olhar só `consultant_id` a deixaria sem
    enxergar o próprio trabalho.

    Escopo vazio vira `false()`, não ausência de filtro: sem recorte resolvido,
    a resposta certa é nenhuma linha — nunca todas.
    """
    condicoes: list[ColumnElement[bool]] = []

    if escopo.colaboradores:
        ids = escopo.colaboradores
        condicoes.append(
            or_(
                ProposalModel.consultant_id.in_(ids),
                ProposalModel.bko_collaborator_id.in_(ids),
                ProposalModel.finalizer_collaborator_id.in_(ids),
            )
        )
    if escopo.registradores:
        condicoes.append(ProposalModel.created_by.in_(escopo.registradores))

    return or_(*condicoes) if condicoes else false()


def ids_de_colaboradores(propostas: Sequence[ProposalModel]) -> set[int]:
    """Ids citados na página, para resolver nomes em uma consulta só (sem N+1)."""
    ids: set[int] = set()
    for proposta in propostas:
        ids.add(proposta.consultant_id)
        for opcional in (proposta.bko_collaborator_id, proposta.finalizer_collaborator_id):
            if opcional is not None:
                ids.add(opcional)
    return ids
