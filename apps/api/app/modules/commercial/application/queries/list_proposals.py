"""Query: listar propostas com filtros e paginação por cursor (seção 7.4).

Os nomes de consultor, BKO e finalizador são resolvidos em **uma** consulta para
a página inteira. O documento do cliente vem mascarado sem `proposals:read_pii`.

Dinheiro sai como string decimal: o frontend exibe o que o backend calculou e
nunca refaz a conta.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    FiltroDePropostas,
    SqlProposalRepository,
    ids_de_colaboradores,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.platform.http.pagination import Cursor, Pagina
from app.platform.security.pii_cipher import PiiCipher
from app.shared.domain.documento import Documento, TipoDeDocumento


@dataclass(frozen=True, slots=True)
class PropostaEmLista:
    id: int
    external_id: str | None
    business_date: date
    customer_name: str
    #: mascarado por padrão; completo apenas com permissão de PII
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
    status: str
    approval_status: str
    version: int


@dataclass(frozen=True, slots=True)
class ListProposals:
    filtro: FiltroDePropostas
    limite: int
    cursor: Cursor | None
    #: `proposals:read_pii` — libera o documento completo do cliente
    pode_ver_pii: bool


class ListProposalsHandler:
    def __init__(
        self,
        *,
        propostas: SqlProposalRepository,
        colaboradores: SqlCollaboratorRepository,
        cipher: PiiCipher,
    ) -> None:
        self._propostas = propostas
        self._colaboradores = colaboradores
        self._cipher = cipher

    async def execute(self, query: ListProposals) -> Pagina[PropostaEmLista]:
        encontradas, tem_mais = await self._propostas.listar(
            filtro=query.filtro, limite=query.limite, cursor=query.cursor
        )

        nomes = await self._nomes(ids_de_colaboradores(encontradas))

        itens = [
            PropostaEmLista(
                id=modelo.id,
                external_id=modelo.external_id,
                business_date=modelo.business_date,
                customer_name=modelo.customer_name,
                customer_document=self._documento(
                    modelo.customer_document_encrypted,
                    modelo.customer_document_type,
                    query.pode_ver_pii,
                ),
                consultant_id=modelo.consultant_id,
                consultant_name=nomes.get(modelo.consultant_id, ""),
                bko_collaborator_id=modelo.bko_collaborator_id,
                finalizer_collaborator_id=modelo.finalizer_collaborator_id,
                operation_amount=f"{modelo.operation_amount:.2f}",
                tps_percentage=f"{modelo.tps_percentage:.6f}",
                company_commission_amount=f"{modelo.company_commission_amount:.2f}",
                paid_amount=f"{modelo.paid_amount_cached:.2f}",
                outstanding_amount=f"{modelo.outstanding_amount_cached:.2f}",
                status=modelo.status,
                approval_status=modelo.approval_status,
                version=modelo.version,
            )
            for modelo in encontradas
        ]

        proximo = None
        if tem_mais and itens:
            ultimo = itens[-1]
            proximo = Cursor(chave=ultimo.business_date.isoformat(), id=ultimo.id).codificar()

        return Pagina(itens=itens, proximo_cursor=proximo)

    async def count(self, filtro: FiltroDePropostas) -> int:
        return await self._propostas.contar(filtro)

    async def _nomes(self, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        return await self._colaboradores.nomes_por_id(tuple(sorted(ids)))

    def _documento(self, cifrado: str, tipo: str, pode_ver_pii: bool) -> str:
        documento = Documento(self._cipher.decifrar(cifrado), TipoDeDocumento(tipo))
        return documento.formatado() if pode_ver_pii else documento.mascarado()
