"""Caso de uso: vincular consultor a líder, com transferência (seção 7.3).

Se já existe vínculo vigente do mesmo tipo, ele é **encerrado em
`novo_inicio - 1 dia`** e o novo é aberto na mesma transação (ADR-0013). Não
existe momento em que o consultor tem dois líderes do mesmo tipo, nem um dia sem
líder no meio.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import (
    ColaboradorInativoError,
    RecursoNaoEncontradoError,
    VigenciaSobrepostaError,
)
from app.modules.organization.domain.value_objects.papel_de_colaborador import PapelDeColaborador
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.teams.domain.policies.compatibilidade_de_papel import garantir_compatibilidade
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock
from app.shared.domain.date_range import DateRange

MODULO = "teams"


@dataclass(frozen=True, slots=True)
class AssignLeader:
    consultant_id: int
    leader_id: int
    assignment_type: str
    start_date: date
    motivo: str
    ator: int | None
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class VinculoCriado:
    id: int
    consultant_id: int
    leader_id: int
    assignment_type: str
    start_date: date
    vinculo_anterior_encerrado_em: date | None


class AssignLeaderHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        vinculos: SqlTeamAssignmentRepository,
        colaboradores: SqlCollaboratorRepository,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._vinculos = vinculos
        self._colaboradores = colaboradores
        self._audit = audit
        self._clock = clock

    async def execute(self, cmd: AssignLeader) -> VinculoCriado:
        if cmd.consultant_id == cmd.leader_id:
            raise VigenciaSobrepostaError("Um colaborador não pode liderar a si mesmo.")

        consultor = await self._exigir_ativo(cmd.consultant_id, "Consultor")
        lider = await self._exigir_ativo(cmd.leader_id, "Líder")

        garantir_compatibilidade(
            tipo_de_vinculo=cmd.assignment_type,
            papeis_do_consultor=await self._papeis_em(consultor.id, cmd.start_date),
            papeis_do_lider=await self._papeis_em(lider.id, cmd.start_date),
        )

        encerrado_em = await self._encerrar_vinculo_vigente(cmd)
        await self._garantir_sem_sobreposicao_futura(cmd)

        vinculo = await self._vinculos.criar(
            consultant_id=cmd.consultant_id,
            leader_id=cmd.leader_id,
            assignment_type=cmd.assignment_type,
            start_date=cmd.start_date,
            end_date=None,
            ator=cmd.ator,
        )

        self._audit.registrar(
            module=MODULO,
            action="assignment.created",
            actor_user_id=cmd.ator,
            aggregate_type="team_assignment",
            aggregate_id=str(vinculo.id),
            correlation_id=cmd.correlation_id,
            payload={
                "consultant_id": cmd.consultant_id,
                "leader_id": cmd.leader_id,
                "assignment_type": cmd.assignment_type,
                "start_date": cmd.start_date.isoformat(),
                "reason": cmd.motivo,
                "previous_closed_on": encerrado_em.isoformat() if encerrado_em else None,
            },
        )
        await self._uow.commit()

        return VinculoCriado(
            id=vinculo.id,
            consultant_id=cmd.consultant_id,
            leader_id=cmd.leader_id,
            assignment_type=cmd.assignment_type,
            start_date=cmd.start_date,
            vinculo_anterior_encerrado_em=encerrado_em,
        )

    async def _exigir_ativo(self, collaborator_id: int, rotulo: str) -> CollaboratorModel:
        colaborador = await self._colaboradores.buscar_por_id(collaborator_id)
        if colaborador is None:
            raise RecursoNaoEncontradoError(f"{rotulo} não encontrado.")
        if not colaborador.is_active:
            raise ColaboradorInativoError(f"{rotulo} está inativo e não pode receber vínculo.")
        return colaborador

    async def _papeis_em(self, collaborator_id: int, referencia: date) -> list[PapelDeColaborador]:
        vigentes = await self._colaboradores.papeis_vigentes_em(collaborator_id, referencia)
        return [PapelDeColaborador(linha.role) for linha in vigentes]

    async def _encerrar_vinculo_vigente(self, cmd: AssignLeader) -> date | None:
        vigente = await self._vinculos.lider_vigente_em(
            consultant_id=cmd.consultant_id,
            assignment_type=cmd.assignment_type,
            referencia=cmd.start_date,
        )
        if vigente is None:
            return None
        if vigente.leader_id == cmd.leader_id:
            raise VigenciaSobrepostaError("O consultor já está vinculado a este líder nesta data.")

        intervalo = DateRange(vigente.start_date, vigente.end_date)
        encerrado = intervalo.encerrar_em(cmd.start_date)
        assert encerrado.fim is not None

        await self._vinculos.encerrar(
            assignment_id=vigente.id,
            end_date=encerrado.fim,
            motivo=f"transferência: {cmd.motivo}",
            quando=self._clock.now(),
            ator=cmd.ator,
        )
        return encerrado.fim

    async def _garantir_sem_sobreposicao_futura(self, cmd: AssignLeader) -> None:
        """Vínculo com início retroativo não pode invadir um intervalo futuro
        já cadastrado."""
        novo = DateRange(cmd.start_date, None)
        for existente in await self._vinculos.do_consultor(
            consultant_id=cmd.consultant_id, assignment_type=cmd.assignment_type
        ):
            if existente.end_date is not None and existente.end_date < cmd.start_date:
                continue
            intervalo = DateRange(existente.start_date, existente.end_date)
            if novo.sobrepoe(intervalo):
                fim = existente.end_date.isoformat() if existente.end_date else "sem fim"
                raise VigenciaSobrepostaError(
                    f"Existe vínculo de {existente.start_date.isoformat()} a {fim} "
                    "que conflita com a data informada."
                )
