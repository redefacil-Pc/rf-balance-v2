"""Equipes e comissões de liderança para homologação local.

python -m app.platform.db.seed_leadership_demo
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commissions.application.group_commission_engine import GroupCommissionEngine
from app.modules.commissions.application.manage_settlements import CommissionSettlementManager
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
    CommissionSettlementModel,
)
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.teams.application.commands.assign_leader import (
    AssignLeader,
    AssignLeaderHandler,
)
from app.modules.teams.infrastructure.models.team_assignment_model import TeamAssignmentModel
from app.modules.teams.infrastructure.repositories.sql_team_assignment_repository import (
    SqlTeamAssignmentRepository,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import SystemClock

PREFIX = "TESTE-COMISSAO-20260817"
LEADER_STRATEGIES = ("COMMERCIAL_LEADER", "GENERAL_MEI_LEADER", "FINALIZATION_LEADER")


@dataclass(frozen=True, slots=True)
class DemoPeople:
    actor: int
    carla: int
    scaled: int
    ana: int
    bruno: int
    elena: int
    fabio: int


class LeadershipDemo:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.engine = criar_engine(self.settings.database)
        self.factory = criar_fabrica_de_sessoes(self.engine)
        self.clock = SystemClock(self.settings.app.app_timezone)
        self.period_end = self.clock.business_date()
        self.period_start = self.period_end - timedelta(days=6)
        self.assignment_start = self.period_end

    async def close(self) -> None:
        await self.engine.dispose()

    async def people(self) -> DemoPeople:
        names = {
            "carla": "Carla Consultora",
            "scaled": "Teste Consultor Escalonado",
            "ana": "Ana Operacional",
            "bruno": "Bruno Lider",
            "elena": "Elena Lider MEI",
            "fabio": "Fabio Lider Final",
        }
        async with self.factory() as session:
            rows = (
                await session.execute(
                    select(CollaboratorModel.full_name, CollaboratorModel.id).where(
                        CollaboratorModel.full_name.in_(names.values())
                    )
                )
            ).all()
            by_name = {str(name): int(identifier) for name, identifier in rows}
            actor = await session.scalar(
                select(UserModel.id).where(UserModel.email == "helio.financeiro@rfbalance.local")
            )
        missing = [name for name in names.values() if name not in by_name]
        if actor is None or missing:
            raise RuntimeError(
                "Massa necessária ausente. Execute seed-demo e seed-commission-demo antes. "
                f"Ausentes: {', '.join(missing) or 'usuário financeiro'}"
            )
        return DemoPeople(
            actor=int(actor),
            **{key: by_name[name] for key, name in names.items()},
        )

    async def ensure_assignment(
        self, *, actor: int, member: int, leader: int, assignment_type: str
    ) -> None:
        async with self.factory() as session:
            existing = await session.scalar(
                select(TeamAssignmentModel.id).where(
                    TeamAssignmentModel.consultant_id == member,
                    TeamAssignmentModel.leader_id == leader,
                    TeamAssignmentModel.assignment_type == assignment_type,
                    TeamAssignmentModel.start_date <= self.assignment_start,
                    func.coalesce(TeamAssignmentModel.end_date, self.period_end)
                    >= self.assignment_start,
                )
            )
        if existing is not None:
            return
        async with UnitOfWork(self.factory) as uow:
            await AssignLeaderHandler(
                uow=uow,
                vinculos=SqlTeamAssignmentRepository(uow.session),
                colaboradores=SqlCollaboratorRepository(uow.session),
                audit=SqlAuditRecorder(uow.session, self.clock),
                clock=self.clock,
            ).execute(
                AssignLeader(
                    consultant_id=member,
                    leader_id=leader,
                    assignment_type=assignment_type,
                    start_date=self.assignment_start,
                    motivo="Equipe isolada para homologar comissões de liderança",
                    ator=actor,
                    correlation_id="seed:leadership-demo",
                )
            )

    async def process_commissions(self) -> None:
        async with self.factory() as session:
            proposal_ids = list(
                (
                    await session.scalars(
                        select(ProposalModel.id).where(ProposalModel.external_id.like(f"{PREFIX}%"))
                    )
                ).all()
            )
        if len(proposal_ids) != 7:
            raise RuntimeError(
                f"Esperadas 7 propostas da massa de comissão; encontradas {len(proposal_ids)}."
            )
        async with UnitOfWork(self.factory) as uow:
            engine = GroupCommissionEngine(uow.session, SqlOutboxRecorder(uow.session, self.clock))
            for proposal_id in proposal_ids:
                await engine.gerar_para_proposta(
                    int(proposal_id), correlation_id="seed:leadership-demo"
                )
            await uow.commit()

    async def generate_settlements(self, actor: int) -> None:
        async with UnitOfWork(self.factory) as uow:
            await CommissionSettlementManager(
                uow=uow,
                audit=SqlAuditRecorder(uow.session, self.clock),
                outbox=SqlOutboxRecorder(uow.session, self.clock),
                clock=self.clock,
            ).generate(
                period_start=self.period_start,
                period_end=self.period_end,
                actor=actor,
                correlation_id="seed:leadership-demo",
            )

    async def validate_and_print(self, people: DemoPeople) -> None:
        leaders = {
            people.bruno: "Bruno Lider",
            people.elena: "Elena Lider MEI",
            people.fabio: "Fabio Lider Final",
        }
        async with self.factory() as session:
            rows = (
                await session.execute(
                    select(
                        CommissionCalculationSnapshotModel.strategy,
                        CommissionEntryModel.beneficiary_id,
                        func.sum(CommissionEntryModel.amount),
                    )
                    .join(
                        CommissionEntryModel,
                        CommissionEntryModel.snapshot_id == CommissionCalculationSnapshotModel.id,
                    )
                    .where(
                        CommissionCalculationSnapshotModel.strategy.in_(LEADER_STRATEGIES),
                        CommissionEntryModel.competence_date >= self.period_start,
                        CommissionEntryModel.competence_date <= self.period_end,
                    )
                    .group_by(
                        CommissionCalculationSnapshotModel.strategy,
                        CommissionEntryModel.beneficiary_id,
                    )
                )
            ).all()
            commissions = {
                (str(strategy), int(beneficiary)): Decimal(amount)
                for strategy, beneficiary, amount in rows
            }
            settlements = {
                item.beneficiary_id: item
                for item in (
                    await session.scalars(
                        select(CommissionSettlementModel).where(
                            CommissionSettlementModel.beneficiary_id.in_(leaders),
                            CommissionSettlementModel.period_start == self.period_start,
                            CommissionSettlementModel.period_end == self.period_end,
                        )
                    )
                ).all()
            }
        expected = {
            ("COMMERCIAL_LEADER", people.bruno),
            ("GENERAL_MEI_LEADER", people.elena),
            ("FINALIZATION_LEADER", people.fabio),
        }
        if not expected.issubset(commissions) or any(commissions[key] <= 0 for key in expected):
            raise RuntimeError(f"Comissões de liderança incompletas: {commissions}")
        print("\nEquipes de demonstração:")
        print("  Bruno Lider       <- Carla + Teste Consultor Escalonado (COMERCIAL)")
        print("  Elena Lider MEI   <- Carla + Teste Consultor Escalonado (MEI_GERAL)")
        print("  Fabio Lider Final <- Ana Operacional (FINALIZACAO)")
        print("\nComissões e fechamentos de liderança:")
        for strategy, leader_id in sorted(expected):
            settlement = settlements.get(leader_id)
            if settlement is None or settlement.gross_amount != commissions[(strategy, leader_id)]:
                raise RuntimeError(f"Fechamento divergente para {leaders[leader_id]}.")
            print(
                f"  {leaders[leader_id]:20} | {strategy:24} | "
                f"bruto=R$ {settlement.gross_amount} | a pagar=R$ {settlement.payable_amount}"
            )


async def execute() -> int:
    demo = LeadershipDemo()
    if demo.settings.app.is_production:
        print("seed de liderança não roda em produção", file=sys.stderr)
        return 1
    try:
        people = await demo.people()
        assignments = (
            (people.carla, people.bruno, "COMERCIAL"),
            (people.scaled, people.bruno, "COMERCIAL"),
            (people.carla, people.elena, "MEI_GERAL"),
            (people.scaled, people.elena, "MEI_GERAL"),
            (people.ana, people.fabio, "FINALIZACAO"),
        )
        for member, leader, assignment_type in assignments:
            await demo.ensure_assignment(
                actor=people.actor,
                member=member,
                leader=leader,
                assignment_type=assignment_type,
            )
        await demo.process_commissions()
        await demo.generate_settlements(people.actor)
        await demo.validate_and_print(people)
        print("\nValidação concluída. Confira Equipes, Fechamentos e Relatório financeiro.")
        return 0
    finally:
        await demo.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(execute()))
