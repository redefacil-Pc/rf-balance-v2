"""Persistência de vínculos consultor-líder (seção 7.3)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.teams.infrastructure.models.team_assignment_model import TeamAssignmentModel


class SqlTeamAssignmentRepository:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self,
        *,
        consultant_id: int,
        leader_id: int,
        assignment_type: str,
        start_date: date,
        end_date: date | None,
        ator: int | None,
    ) -> TeamAssignmentModel:
        modelo = TeamAssignmentModel(
            consultant_id=consultant_id,
            leader_id=leader_id,
            assignment_type=assignment_type,
            start_date=start_date,
            end_date=end_date,
            created_by=ator,
        )
        self._session.add(modelo)
        await self._session.flush()
        return modelo

    async def buscar_por_id(self, assignment_id: int) -> TeamAssignmentModel | None:
        encontrado: TeamAssignmentModel | None = await self._session.scalar(
            select(TeamAssignmentModel).where(TeamAssignmentModel.id == assignment_id)
        )
        return encontrado

    async def do_consultor(
        self, *, consultant_id: int, assignment_type: str | None = None
    ) -> list[TeamAssignmentModel]:
        consulta = select(TeamAssignmentModel).where(
            TeamAssignmentModel.consultant_id == consultant_id
        )
        if assignment_type is not None:
            consulta = consulta.where(TeamAssignmentModel.assignment_type == assignment_type)
        return list(
            (await self._session.scalars(consulta.order_by(TeamAssignmentModel.start_date))).all()
        )

    async def lider_vigente_em(
        self, *, consultant_id: int, assignment_type: str, referencia: date
    ) -> TeamAssignmentModel | None:
        """A consulta da seção 7.3, literal. É o caminho crítico da F4."""
        vigente: TeamAssignmentModel | None = await self._session.scalar(
            select(TeamAssignmentModel).where(
                TeamAssignmentModel.consultant_id == consultant_id,
                TeamAssignmentModel.assignment_type == assignment_type,
                TeamAssignmentModel.start_date <= referencia,
                or_(
                    TeamAssignmentModel.end_date.is_(None),
                    TeamAssignmentModel.end_date >= referencia,
                ),
            )
        )
        return vigente

    async def equipe_do_lider_em(
        self, *, leader_id: int, referencia: date, assignment_type: str | None = None
    ) -> list[TeamAssignmentModel]:
        consulta = select(TeamAssignmentModel).where(
            TeamAssignmentModel.leader_id == leader_id,
            TeamAssignmentModel.start_date <= referencia,
            or_(
                TeamAssignmentModel.end_date.is_(None),
                TeamAssignmentModel.end_date >= referencia,
            ),
        )
        if assignment_type is not None:
            consulta = consulta.where(TeamAssignmentModel.assignment_type == assignment_type)
        return list((await self._session.scalars(consulta)).all())

    async def encerrar(
        self,
        *,
        assignment_id: int,
        end_date: date,
        motivo: str,
        quando: datetime,
        ator: int | None,
    ) -> None:
        await self._session.execute(
            update(TeamAssignmentModel)
            .where(TeamAssignmentModel.id == assignment_id)
            .values(
                end_date=end_date,
                closing_reason=motivo,
                updated_at=quando,
                updated_by=ator,
            )
        )
