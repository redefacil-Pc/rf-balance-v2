"""Queries de usuário: listagem paginada e detalhe.

Os papéis da página inteira saem em **uma** consulta, não uma por usuário — o
mesmo N+1 que a listagem de colaboradores evita.

Hash de senha nunca sai daqui: não está no DTO, então não há como vazar por
descuido de serialização.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.errors import UsuarioNaoEncontradoError
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.identity.infrastructure.repositories.sql_user_repository import (
    FiltroDeUsuarios,
    SqlUserRepository,
)
from app.platform.http.pagination import Cursor, Pagina


@dataclass(frozen=True, slots=True)
class UsuarioEmLista:
    id: int
    email: str
    full_name: str
    is_active: bool
    must_change_password: bool
    roles: tuple[str, ...]
    last_login_at: datetime | None
    #: colaborador vinculado, quando a pessoa também é cadastrada como tal
    collaborator_id: int | None


@dataclass(frozen=True, slots=True)
class ListUsers:
    filtro: FiltroDeUsuarios
    limite: int
    cursor: Cursor | None


@dataclass(frozen=True, slots=True)
class GetUser:
    user_id: int


class ListUsersHandler:
    def __init__(self, *, users: SqlUserRepository) -> None:
        self._users = users

    async def execute(self, query: ListUsers) -> Pagina[UsuarioEmLista]:
        encontrados, tem_mais = await self._users.listar(
            filtro=query.filtro, limite=query.limite, cursor=query.cursor
        )
        ids = [u.id for u in encontrados]
        papeis = await self._users.papeis_de_varios(ids)
        colaboradores = await self._users.colaboradores_de_varios(ids)

        itens = [
            _montar(modelo, papeis.get(modelo.id, []), colaboradores.get(modelo.id))
            for modelo in encontrados
        ]

        proximo = None
        if tem_mais and itens:
            ultimo = encontrados[-1]
            proximo = Cursor(chave=ultimo.full_name, id=ultimo.id).codificar()

        return Pagina(itens=itens, proximo_cursor=proximo)


class GetUserHandler:
    def __init__(self, *, users: SqlUserRepository) -> None:
        self._users = users

    async def execute(self, query: GetUser) -> UsuarioEmLista:
        modelo = await self._users.linha(query.user_id)
        if modelo is None:
            raise UsuarioNaoEncontradoError(f"Usuário {query.user_id} não encontrado.")
        papeis = (await self._users.papeis_de_varios([modelo.id])).get(modelo.id, [])
        colaborador = (await self._users.colaboradores_de_varios([modelo.id])).get(modelo.id)
        return _montar(modelo, papeis, colaborador)


def _montar(modelo: UserModel, papeis: list[str], colaborador_id: int | None) -> UsuarioEmLista:
    return UsuarioEmLista(
        id=modelo.id,
        email=modelo.email,
        full_name=modelo.full_name,
        is_active=modelo.is_active,
        must_change_password=modelo.must_change_password,
        roles=tuple(papeis),
        last_login_at=modelo.last_login_at,
        collaborator_id=colaborador_id,
    )
