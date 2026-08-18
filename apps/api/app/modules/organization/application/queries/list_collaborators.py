"""Query: listar colaboradores com filtros e paginação por cursor.

Papéis vigentes são resolvidos em **uma** consulta para a página inteira. O
documento e o PIX só são decifrados quando quem consulta tem permissão de PII;
sem ela, o retorno traz apenas o valor mascarado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    FiltroDeColaboradores,
    SqlCollaboratorRepository,
)
from app.platform.http.pagination import Cursor, Pagina
from app.platform.security.pii_cipher import PiiCipher
from app.shared.domain.documento import Documento, TipoDeDocumento


@dataclass(frozen=True, slots=True)
class ColaboradorEmLista:
    id: int
    full_name: str
    company_id: int
    unit_id: int | None
    tax_regime: str
    is_active: bool
    roles: list[str]
    #: mascarado por padrão; completo apenas com permissão de PII
    document: str
    document_type: str
    #: conta de acesso vinculada; nulo para quem não usa o sistema
    user_id: int | None
    user_full_name: str | None
    user_email: str | None
    user_is_active: bool | None


@dataclass(frozen=True, slots=True)
class ListCollaborators:
    filtro: FiltroDeColaboradores
    limite: int
    cursor: Cursor | None
    referencia: date
    #: `collaborators:read_pii` — libera documento completo e PIX
    pode_ver_pii: bool


class ListCollaboratorsHandler:
    def __init__(self, *, colaboradores: SqlCollaboratorRepository, cipher: PiiCipher) -> None:
        self._colaboradores = colaboradores
        self._cipher = cipher

    async def execute(self, query: ListCollaborators) -> Pagina[ColaboradorEmLista]:
        encontrados, tem_mais = await self._colaboradores.listar(
            filtro=query.filtro,
            limite=query.limite,
            cursor=query.cursor,
            referencia=query.referencia,
        )

        papeis = await self._colaboradores.papeis_vigentes_de_varios(
            [modelo.id for modelo in encontrados], query.referencia
        )
        contas = await self._colaboradores.contas_de_varios([modelo.id for modelo in encontrados])

        itens = [
            ColaboradorEmLista(
                id=modelo.id,
                full_name=modelo.full_name,
                company_id=modelo.company_id,
                unit_id=modelo.unit_id,
                tax_regime=modelo.tax_regime,
                is_active=modelo.is_active,
                roles=sorted(papeis.get(modelo.id, [])),
                document=self._documento(modelo.document_encrypted, query.pode_ver_pii),
                document_type=modelo.document_type,
                user_id=modelo.user_id,
                user_full_name=contas.get(modelo.id, (0, "", "", False))[1] or None,
                user_email=contas.get(modelo.id, (0, "", "", False))[2] or None,
                user_is_active=(contas[modelo.id][3] if modelo.id in contas else None),
            )
            for modelo in encontrados
        ]

        proximo = None
        if tem_mais and itens:
            ultimo = itens[-1]
            proximo = Cursor(chave=ultimo.full_name, id=ultimo.id).codificar()

        return Pagina(itens=itens, proximo_cursor=proximo)

    def _documento(self, cifrado: str, pode_ver_pii: bool) -> str:
        digitos = self._cipher.decifrar(cifrado)
        tipo = TipoDeDocumento.CPF if len(digitos) == 11 else TipoDeDocumento.CNPJ
        documento = Documento(digitos, tipo)
        return documento.formatado() if pode_ver_pii else documento.mascarado()
