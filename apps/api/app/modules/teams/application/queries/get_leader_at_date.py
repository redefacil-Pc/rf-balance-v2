"""Query: qual líder valia para este consultor numa data (seção 7.3).

É consulta de primeira classe, não derivação de tela: o motor de comissão da F4
depende dela para decidir quem recebe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)


@dataclass(frozen=True, slots=True)
class LiderNaData:
    assignment_id: int
    leader_id: int
    leader_name: str
    assignment_type: str
    start_date: date
    end_date: date | None


class GetLeaderAtDateHandler:
    def __init__(
        self,
        *,
        vinculos: SqlTeamAssignmentRepository,
        colaboradores: SqlCollaboratorRepository,
    ) -> None:
        self._vinculos = vinculos
        self._colaboradores = colaboradores

    async def execute(
        self, *, consultant_id: int, assignment_type: str, referencia: date
    ) -> LiderNaData | None:
        vinculo = await self._vinculos.lider_vigente_em(
            consultant_id=consultant_id,
            assignment_type=assignment_type,
            referencia=referencia,
        )
        if vinculo is None:
            return None

        lider = await self._colaboradores.buscar_por_id(vinculo.leader_id)
        return LiderNaData(
            assignment_id=vinculo.id,
            leader_id=vinculo.leader_id,
            leader_name=lider.full_name if lider else "",
            assignment_type=vinculo.assignment_type,
            start_date=vinculo.start_date,
            end_date=vinculo.end_date,
        )
