"""Caso de uso: inativar colaborador (seção 7.2).

Inativação exige data e motivo, e **encerra os vínculos ativos** na mesma
transação — colaborador inativo não pode continuar liderando ou sendo liderado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import RecursoNaoEncontradoError
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

MODULO = "organization"


@dataclass(frozen=True, slots=True)
class DeactivateCollaborator:
    collaborator_id: int
    em: date
    motivo: str
    ator: int | None
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class ColaboradorInativado:
    id: int
    vinculos_encerrados: int


class DeactivateCollaboratorHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        colaboradores: SqlCollaboratorRepository,
        vinculos: SqlTeamAssignmentRepository,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._colaboradores = colaboradores
        self._vinculos = vinculos
        self._audit = audit
        self._clock = clock

    async def execute(self, cmd: DeactivateCollaborator) -> ColaboradorInativado:
        colaborador = await self._colaboradores.buscar_por_id(cmd.collaborator_id)
        if colaborador is None:
            raise RecursoNaoEncontradoError("Colaborador não encontrado.")

        agora = self._clock.now()
        encerrados = 0

        # como consultor
        for vinculo in await self._vinculos.do_consultor(consultant_id=cmd.collaborator_id):
            if vinculo.end_date is None:
                await self._vinculos.encerrar(
                    assignment_id=vinculo.id,
                    end_date=cmd.em,
                    motivo=f"inativação do colaborador: {cmd.motivo}",
                    quando=agora,
                    ator=cmd.ator,
                )
                encerrados += 1

        # como líder
        for vinculo in await self._vinculos.equipe_do_lider_em(
            leader_id=cmd.collaborator_id, referencia=cmd.em
        ):
            if vinculo.end_date is None:
                await self._vinculos.encerrar(
                    assignment_id=vinculo.id,
                    end_date=cmd.em,
                    motivo=f"inativação do líder: {cmd.motivo}",
                    quando=agora,
                    ator=cmd.ator,
                )
                encerrados += 1

        await self._colaboradores.inativar(
            collaborator_id=cmd.collaborator_id,
            em=cmd.em,
            motivo=cmd.motivo,
            quando=agora,
            ator=cmd.ator,
        )

        self._audit.registrar(
            module=MODULO,
            action="collaborator.deactivated",
            actor_user_id=cmd.ator,
            aggregate_type="collaborator",
            aggregate_id=str(cmd.collaborator_id),
            correlation_id=cmd.correlation_id,
            payload={
                "deactivated_on": cmd.em.isoformat(),
                "reason": cmd.motivo,
                "closed_assignments": encerrados,
            },
        )
        await self._uow.commit()

        return ColaboradorInativado(id=cmd.collaborator_id, vinculos_encerrados=encerrados)
