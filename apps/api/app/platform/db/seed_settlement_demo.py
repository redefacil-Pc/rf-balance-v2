"""Massa local idempotente para demonstrar fechamento, carryover e pagamento.

python -m app.platform.db.seed_settlement_demo
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.commissions.application.manage_periods import CommissionPeriodManager
from app.modules.commissions.application.manage_settlements import CommissionSettlementManager
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionPeriodModel,
    CommissionSettlementModel,
)
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.organization.application.commands.create_collaborator import (
    CreateCollaborator,
    CreateCollaboratorHandler,
    PapelSolicitado,
)
from app.modules.organization.domain.value_objects.papel_de_colaborador import (
    PapelDeColaborador,
    RegimeTributario,
)
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security import pii_cipher as pii
from app.platform.time.clock import SystemClock


class SettlementDemo:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.engine = criar_engine(self.settings.database)
        self.factory = criar_fabrica_de_sessoes(self.engine)
        self.clock = SystemClock(self.settings.app.app_timezone)
        self.cipher = pii.criar(self.settings.pii.chave, self.settings.pii.pepper)
        self.current_end = self.clock.business_date()
        self.current_start = self.current_end - timedelta(days=6)
        self.previous_start = self.current_start - timedelta(days=14)
        self.previous_end = self.current_end - timedelta(days=14)

    async def close(self) -> None:
        await self.engine.dispose()

    def manager(self, uow: UnitOfWork) -> CommissionSettlementManager:
        return CommissionSettlementManager(
            uow=uow,
            audit=SqlAuditRecorder(uow.session, self.clock),
            outbox=SqlOutboxRecorder(uow.session, self.clock),
            clock=self.clock,
        )

    def period_manager(self, uow: UnitOfWork) -> CommissionPeriodManager:
        return CommissionPeriodManager(
            uow=uow,
            audit=SqlAuditRecorder(uow.session, self.clock),
            outbox=SqlOutboxRecorder(uow.session, self.clock),
            clock=self.clock,
        )

    async def prerequisites(self) -> tuple[int, int, int, int]:
        async with self.factory() as session:
            actor = await session.scalar(
                select(UserModel.id).where(UserModel.email == "helio.financeiro@rfbalance.local")
            )
            source = await session.scalar(
                select(CollaboratorModel).where(CollaboratorModel.full_name == "Gisele BKO")
            )
            scaled = await session.scalar(
                select(CollaboratorModel.id).where(
                    CollaboratorModel.full_name == "Teste Consultor Escalonado"
                )
            )
            if actor is None or source is None or scaled is None:
                raise RuntimeError(
                    "Execute antes os seeds demo e de comissionamento para criar os beneficiários."
                )
            source_data = (source.id, source.company_id, source.unit_id)
        bko = await self.ensure_demo_bko(int(actor), source_data[1], source_data[2])
        finalizer = await self.ensure_demo_finalizer(int(actor), source_data[1], source_data[2])
        return int(actor), bko, int(scaled), finalizer

    async def ensure_demo_bko(self, actor: int, company_id: int, unit_id: int | None) -> int:
        async with self.factory() as session:
            existing = await session.scalar(
                select(CollaboratorModel.id).where(
                    CollaboratorModel.full_name == "Teste BKO Carryover"
                )
            )
        if existing is not None:
            return int(existing)
        async with UnitOfWork(self.factory) as uow:
            created = await CreateCollaboratorHandler(
                uow=uow,
                colaboradores=SqlCollaboratorRepository(uow.session),
                empresas=SqlCompanyRepository(uow.session),
                cipher=self.cipher,
                audit=SqlAuditRecorder(uow.session, self.clock),
                clock=self.clock,
            ).execute(
                CreateCollaborator(
                    company_id=company_id,
                    unit_id=unit_id,
                    full_name="Teste BKO Carryover",
                    documento="987.654.321-00",
                    regime=RegimeTributario.MEI,
                    papeis=(
                        PapelSolicitado(
                            papel=PapelDeColaborador.BKO,
                            valid_from=date(2026, 1, 1),
                        ),
                    ),
                    ator=actor,
                )
            )
            return created.id

    async def ensure_demo_finalizer(self, actor: int, company_id: int, unit_id: int | None) -> int:
        async with self.factory() as session:
            existing = await session.scalar(
                select(CollaboratorModel.id).where(
                    CollaboratorModel.full_name == "Teste Finalização Manual"
                )
            )
        if existing is not None:
            return int(existing)
        async with UnitOfWork(self.factory) as uow:
            created = await CreateCollaboratorHandler(
                uow=uow,
                colaboradores=SqlCollaboratorRepository(uow.session),
                empresas=SqlCompanyRepository(uow.session),
                cipher=self.cipher,
                audit=SqlAuditRecorder(uow.session, self.clock),
                clock=self.clock,
            ).execute(
                CreateCollaborator(
                    company_id=company_id,
                    unit_id=unit_id,
                    full_name="Teste Finalização Manual",
                    documento="800.000.019-96",
                    regime=RegimeTributario.CLT,
                    papeis=(
                        PapelSolicitado(
                            papel=PapelDeColaborador.FINALIZACAO,
                            valid_from=date(2026, 1, 1),
                        ),
                    ),
                    ator=actor,
                )
            )
            return created.id

    async def ensure_entries(self, actor: int, bko: int, finalizer: int) -> None:
        entries = (
            (
                Decimal("200.00"),
                self.previous_end,
                "BKO anterior para demonstrar carryover",
                "seed-settlement-bko-previous-20260806",
            ),
            (
                Decimal("300.00"),
                self.clock.business_date(),
                "BKO atual para demonstrar carryover e ajustes",
                "seed-settlement-bko-current-20260817-v2",
            ),
        )
        for amount, effective_date, description, key in entries:
            async with UnitOfWork(self.factory) as uow:
                await self.manager(uow).add_bko_entry(
                    beneficiary_id=bko,
                    amount=amount,
                    effective_date=effective_date,
                    description=description,
                    idempotency_key=key,
                    actor=actor,
                    correlation_id="seed:settlement-demo",
                )
        async with UnitOfWork(self.factory) as uow:
            await self.manager(uow).add_finalization_entry(
                beneficiary_id=finalizer,
                amount=Decimal("300.00"),
                effective_date=self.clock.business_date(),
                description="Bônus manual para demonstrar Finalização",
                idempotency_key="seed-settlement-finalization-current-20260817",
                actor=actor,
                correlation_id="seed:settlement-demo",
            )

    async def generate(self, actor: int, start: date, end: date) -> None:
        async with UnitOfWork(self.factory) as uow:
            await self.manager(uow).generate(
                period_start=start,
                period_end=end,
                actor=actor,
                correlation_id="seed:settlement-demo",
            )

    async def settlement(
        self, beneficiary: int, start: date, end: date
    ) -> CommissionSettlementModel:
        async with self.factory() as session:
            model = await session.scalar(
                select(CommissionSettlementModel).where(
                    CommissionSettlementModel.beneficiary_id == beneficiary,
                    CommissionSettlementModel.period_start == start,
                    CommissionSettlementModel.period_end == end,
                )
            )
            if model is None:
                raise RuntimeError(f"Fechamento de {beneficiary} não encontrado em {start}:{end}.")
            session.expunge(model)
            return model

    async def adjust(
        self,
        actor: int,
        settlement_id: int,
        *,
        bonus: str = "0",
        discount: str = "0",
        deferred: str = "0",
        notes: str,
    ) -> None:
        model = await self._by_id(settlement_id)
        if model.status == "PAID":
            return
        async with UnitOfWork(self.factory) as uow:
            await self.manager(uow).adjust(
                settlement_id=settlement_id,
                bonus_amount=Decimal(bonus),
                discount_amount=Decimal(discount),
                deferred_amount=Decimal(deferred),
                notes=notes,
                actor=actor,
                correlation_id="seed:settlement-demo",
            )

    async def pay_until(
        self, actor: int, settlement_id: int, target: Decimal, reference: str
    ) -> None:
        model = await self._by_id(settlement_id)
        missing = target - model.paid_amount
        if missing <= 0:
            return
        async with UnitOfWork(self.factory) as uow:
            await self.manager(uow).pay(
                settlement_id=settlement_id,
                amount=missing,
                payment_date=self.clock.business_date(),
                payment_method="PIX",
                reference=reference,
                actor=actor,
                correlation_id="seed:settlement-demo",
            )

    async def _by_id(self, settlement_id: int) -> CommissionSettlementModel:
        async with self.factory() as session:
            model = await session.get(CommissionSettlementModel, settlement_id)
            if model is None:
                raise RuntimeError("Fechamento de demonstração não encontrado.")
            session.expunge(model)
            return model

    async def ensure_period(self, actor: int, start: date, end: date, *, close: bool) -> None:
        async with self.factory() as session:
            period = await session.scalar(
                select(CommissionPeriodModel).where(
                    CommissionPeriodModel.period_start == start,
                    CommissionPeriodModel.period_end == end,
                )
            )
            period_id = None if period is None else period.id
            status = None if period is None else period.status
        if period_id is None:
            zone = ZoneInfo(self.settings.app.app_timezone)
            cutoff = datetime.combine(end, datetime.max.time(), tzinfo=zone)
            async with UnitOfWork(self.factory) as uow:
                period = await self.period_manager(uow).create(
                    period_start=start,
                    period_end=end,
                    cutoff_at=cutoff,
                    reason="Período de demonstração do fechamento",
                    actor=actor,
                    correlation_id="seed:settlement-demo",
                )
                period_id, status = period.id, period.status
        if close and status == "OPEN":
            async with UnitOfWork(self.factory) as uow:
                await self.period_manager(uow).close(
                    period_id=int(period_id),
                    reason="Período anterior conferido na homologação",
                    actor=actor,
                    correlation_id="seed:settlement-demo",
                )

    async def period_is_closed(self, start: date, end: date) -> bool:
        async with self.factory() as session:
            status = await session.scalar(
                select(CommissionPeriodModel.status).where(
                    CommissionPeriodModel.period_start == start,
                    CommissionPeriodModel.period_end == end,
                )
            )
            return status == "CLOSED"

    async def validate_and_print(self, bko: int, scaled: int, finalizer: int) -> None:
        cases = (
            (
                bko,
                self.previous_start,
                self.previous_end,
                "200.00",
                "0.00",
                "0.00",
                "0.00",
                "80.00",
                "120.00",
                "0.00",
                "DEFERRED",
            ),
            (
                bko,
                self.current_start,
                self.current_end,
                "300.00",
                "80.00",
                "50.00",
                "20.00",
                "100.00",
                "200.00",
                "110.00",
                "DEFERRED",
            ),
            (
                scaled,
                self.current_start,
                self.current_end,
                "2800.00",
                "0.00",
                "0.00",
                "0.00",
                "0.00",
                "2800.00",
                "0.00",
                "PAID",
            ),
            (
                finalizer,
                self.current_start,
                self.current_end,
                "0.00",
                "0.00",
                "300.00",
                "0.00",
                "0.00",
                "0.00",
                "300.00",
                "PENDING",
            ),
        )
        async with self.factory() as session:
            names = {
                row.id: row.full_name
                for row in (
                    await session.scalars(
                        select(CollaboratorModel).where(
                            CollaboratorModel.id.in_((bko, scaled, finalizer))
                        )
                    )
                ).all()
            }
        print("\nFechamentos de demonstração:")
        for beneficiary, start, end, *wanted in cases:
            model = await self.settlement(beneficiary, start, end)
            actual = [
                str(model.gross_amount),
                str(model.carryover_amount),
                str(model.bonus_amount),
                str(model.discount_amount),
                str(model.deferred_amount),
                str(model.paid_amount),
                str(model.payable_amount),
                model.status,
            ]
            if actual != wanted:
                raise RuntimeError(
                    f"Fechamento {names[beneficiary]} divergiu: {actual} != {wanted}"
                )
            print(
                f"  {start:%d/%m} a {end:%d/%m} | {names[beneficiary]:28} | "
                f"bruto={wanted[0]:>8} carryover={wanted[1]:>6} bônus={wanted[2]:>6} "
                f"desconto={wanted[3]:>6} adiado={wanted[4]:>6} pago={wanted[5]:>8} "
                f"a pagar={wanted[6]:>8} {wanted[7]}"
            )


async def execute() -> int:
    demo = SettlementDemo()
    if demo.settings.app.is_production:
        print("seed de fechamento não roda em produção", file=sys.stderr)
        return 1
    try:
        actor, bko, scaled, finalizer = await demo.prerequisites()
        await demo.ensure_entries(actor, bko, finalizer)

        if not await demo.period_is_closed(demo.previous_start, demo.previous_end):
            await demo.generate(actor, demo.previous_start, demo.previous_end)
            previous = await demo.settlement(bko, demo.previous_start, demo.previous_end)
            await demo.adjust(
                actor,
                previous.id,
                deferred="80",
                notes="R$ 80,00 adiados para demonstrar carryover",
            )
            await demo.pay_until(actor, previous.id, Decimal("120.00"), "DEMO-BKO-ANTERIOR")
            await demo.ensure_period(
                actor, demo.previous_start, demo.previous_end, close=True
            )

        await demo.ensure_period(actor, demo.current_start, demo.current_end, close=False)
        await demo.generate(actor, demo.current_start, demo.current_end)
        current = await demo.settlement(bko, demo.current_start, demo.current_end)
        await demo.adjust(
            actor,
            current.id,
            bonus="50",
            discount="20",
            deferred="100",
            notes="Demonstração BKO: carryover, bônus, desconto e adiamento",
        )
        await demo.pay_until(actor, current.id, Decimal("200.00"), "DEMO-BKO-PARCIAL")

        scaled_current = await demo.settlement(scaled, demo.current_start, demo.current_end)
        await demo.pay_until(actor, scaled_current.id, Decimal("2800.00"), "DEMO-ESCALONADO")

        await demo.validate_and_print(bko, scaled, finalizer)
        print(
            "\nValidação concluída. Abra Fechamentos no período "
            f"{demo.current_start:%d/%m} a {demo.current_end:%d/%m}."
        )
        return 0
    finally:
        await demo.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(execute()))
