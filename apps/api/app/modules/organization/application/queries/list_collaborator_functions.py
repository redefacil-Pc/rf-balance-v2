"""Query: funções de um colaborador, vigentes e encerradas.

Devolve o histórico inteiro, não só o que vale hoje: a tela precisa mostrar que
a pessoa foi BKO até março e é finalização desde então — sem isso, a comissão de
uma proposta antiga parece calculada pela função errada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.organization.domain.errors import RecursoNaoEncontradoError
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)


@dataclass(frozen=True, slots=True)
class FuncaoEmLista:
    id: int
    role: str
    valid_from: date
    valid_to: date | None
    #: vigente na data de referência do sistema
    current: bool


@dataclass(frozen=True, slots=True)
class ListCollaboratorFunctions:
    collaborator_id: int
    referencia: date


class ListCollaboratorFunctionsHandler:
    def __init__(self, *, colaboradores: SqlCollaboratorRepository) -> None:
        self._colaboradores = colaboradores

    async def execute(self, query: ListCollaboratorFunctions) -> list[FuncaoEmLista]:
        if await self._colaboradores.buscar_por_id(query.collaborator_id) is None:
            raise RecursoNaoEncontradoError("Colaborador não encontrado.")

        linhas = await self._colaboradores.papeis_do_colaborador(query.collaborator_id)

        return sorted(
            (
                FuncaoEmLista(
                    id=linha.id,
                    role=linha.role,
                    valid_from=linha.valid_from,
                    valid_to=linha.valid_to,
                    current=_vigente(linha.valid_from, linha.valid_to, query.referencia),
                )
                for linha in linhas
            ),
            # vigente primeiro, depois da mais recente para a mais antiga
            key=lambda f: (not f.current, -f.valid_from.toordinal()),
        )


def _vigente(inicio: date, fim: date | None, referencia: date) -> bool:
    return inicio <= referencia and (fim is None or fim >= referencia)
