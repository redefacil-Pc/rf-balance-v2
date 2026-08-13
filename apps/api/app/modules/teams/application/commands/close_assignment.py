from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import (
    RecursoNaoEncontradoError,
    VigenciaSobrepostaError,
)
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock


@dataclass(frozen=True, slots=True)
class CloseAssignment:
    assignment_id: int
    end_date: date
    reason: str
    actor: int | None
    correlation_id: str | None


class CloseAssignmentHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        assignments: SqlTeamAssignmentRepository,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._assignments = assignments
        self._audit = audit
        self._clock = clock

    async def execute(self, cmd: CloseAssignment) -> None:
        model = await self._assignments.buscar_por_id(cmd.assignment_id)
        if model is None:
            raise RecursoNaoEncontradoError("Vínculo não encontrado.")
        if model.end_date is not None:
            raise VigenciaSobrepostaError("Este vínculo já está encerrado.")
        if cmd.end_date < model.start_date:
            raise VigenciaSobrepostaError("A data final não pode ser anterior ao início.")
        await self._assignments.encerrar(
            assignment_id=model.id,
            end_date=cmd.end_date,
            motivo=cmd.reason,
            quando=self._clock.now(),
            ator=cmd.actor,
        )
        self._audit.registrar(
            module="teams",
            action="assignment.closed",
            actor_user_id=cmd.actor,
            aggregate_type="team_assignment",
            aggregate_id=str(model.id),
            correlation_id=cmd.correlation_id,
            payload={"end_date": cmd.end_date.isoformat(), "reason": cmd.reason},
        )
        await self._uow.commit()
