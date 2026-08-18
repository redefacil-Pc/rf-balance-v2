"""Consulta consolidada dos vínculos de equipe vigentes em uma data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.teams.infrastructure.models.team_assignment_model import TeamAssignmentModel


@dataclass(frozen=True, slots=True)
class ActiveTeamAssignment:
    id: int
    member_id: int
    member_name: str
    leader_id: int
    leader_name: str
    assignment_type: str
    start_date: date
    end_date: date | None


class ListActiveTeamsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, reference_date: date) -> list[ActiveTeamAssignment]:
        member = aliased(CollaboratorModel, name="member")
        leader = aliased(CollaboratorModel, name="leader")
        result = await self._session.execute(
            select(
                TeamAssignmentModel,
                member.full_name,
                leader.full_name,
            )
            .join(member, member.id == TeamAssignmentModel.consultant_id)
            .join(leader, leader.id == TeamAssignmentModel.leader_id)
            .where(
                TeamAssignmentModel.start_date <= reference_date,
                or_(
                    TeamAssignmentModel.end_date.is_(None),
                    TeamAssignmentModel.end_date >= reference_date,
                ),
            )
            .order_by(
                TeamAssignmentModel.assignment_type,
                leader.full_name,
                member.full_name,
            )
        )
        return [
            ActiveTeamAssignment(
                id=assignment.id,
                member_id=assignment.consultant_id,
                member_name=member_name,
                leader_id=assignment.leader_id,
                leader_name=leader_name,
                assignment_type=assignment.assignment_type,
                start_date=assignment.start_date,
                end_date=assignment.end_date,
            )
            for assignment, member_name, leader_name in result.all()
        ]
