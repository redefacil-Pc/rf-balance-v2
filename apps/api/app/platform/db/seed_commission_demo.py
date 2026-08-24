"""Cria cenários locais, rastreáveis e idempotentes de comissionamento.

    python -m app.platform.db.seed_commission_demo

Não roda em produção. Toda proposta passa pelos mesmos casos de uso usados
pela API: cadastro, declaração, envio, aprovação, estorno e nova conferência.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.commercial.application.commands.create_proposal import (
    CreateProposal,
    CreateProposalHandler,
)
from app.modules.commercial.application.commands.decide_proposal import (
    DecideProposal,
    DecideProposalHandler,
    Decisao,
)
from app.modules.commercial.application.commands.submit_proposal import (
    SubmitProposal,
    SubmitProposalHandler,
)
from app.modules.commercial.application.ports.proposal_scope import EscopoDePropostas
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commercial.infrastructure.repositories.sql_proposal_repository import (
    SqlProposalRepository,
)
from app.modules.commercial.infrastructure.storage.object_attachment_storage import (
    ObjectAttachmentStorage,
)
from app.modules.commissions.application.standard_commission_engine import (
    StandardCommissionEngine,
)
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
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
from app.modules.organization.infrastructure.models.receiving_account_model import (
    ReceivingAccountModel,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.modules.organization.infrastructure.repositories.sql_receiving_account_directory import (
    SqlReceivingAccountDirectory,
)
from app.modules.receivables.application.receipt_service import ReceiptService
from app.modules.receivables.infrastructure.models.receipt_model import ReceiptModel
from app.modules.receivables.infrastructure.recognizers.sql_receipt_recognizer import (
    SqlReceiptRecognizer,
)
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security import pii_cipher as pii
from app.platform.storage.object_storage import criar_cliente
from app.platform.time.clock import SystemClock

PREFIXO = "TESTE-COMISSAO-20260817"
CPF_CLIENTE = "111.444.777-35"
COMPROVANTE = b"%PDF-1.4\nCenario local de homologacao RF Balance\n"


@dataclass(frozen=True, slots=True)
class Contexto:
    consultant_id: int
    finalizer_id: int
    launcher_user_id: int
    finance_user_id: int


class Populador:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.engine = criar_engine(self.settings.database)
        self.factory = criar_fabrica_de_sessoes(self.engine)
        self.clock = SystemClock(self.settings.app.app_timezone)
        self.cipher = pii.criar(self.settings.pii.chave, self.settings.pii.pepper)
        self.storage = ObjectAttachmentStorage(
            criar_cliente(self.settings.storage),
            self.settings.storage.object_storage_bucket,
            self.settings.storage.object_storage_prefix,
        )
        self.today = self.clock.business_date()
        self.receiving_account_id = 0

    async def close(self) -> None:
        await self.engine.dispose()

    async def conta_de_recebimento(self) -> int:
        """Conta usada pela massa. Idempotente: reaproveita a que já existir."""
        rotulo = "Conta de homologação (SEED)"
        async with self.factory() as session:
            existente = await session.scalar(
                select(ReceivingAccountModel.id).where(ReceivingAccountModel.label == rotulo)
            )
            if existente is not None:
                return int(existente)
            conta = ReceivingAccountModel(label=rotulo, display_order=999, is_active=True)
            session.add(conta)
            await session.commit()
            return int(conta.id)

    async def context(self) -> tuple[Contexto, int]:
        async with self.factory() as session:
            carla = await session.scalar(
                select(CollaboratorModel).where(CollaboratorModel.full_name == "Carla Consultora")
            )
            finalizer = await session.scalar(
                select(CollaboratorModel).where(CollaboratorModel.full_name == "Ana Operacional")
            )
            launcher = await session.scalar(
                select(UserModel).where(UserModel.email == "ana.operacional@rfbalance.local")
            )
            finance = await session.scalar(
                select(UserModel).where(UserModel.email == "helio.financeiro@rfbalance.local")
            )
            if carla is None or finalizer is None or launcher is None or finance is None:
                raise RuntimeError(
                    "Massa base ausente. Execute primeiro: python -m app.platform.db.seed_demo"
                )
            scaled_id = await self._ensure_scaled(
                company_id=carla.company_id,
                unit_id=carla.unit_id,
                actor=finance.id,
            )
            return (
                Contexto(
                    consultant_id=carla.id,
                    finalizer_id=finalizer.id,
                    launcher_user_id=launcher.id,
                    finance_user_id=finance.id,
                ),
                scaled_id,
            )

    async def _ensure_scaled(self, *, company_id: int, unit_id: int | None, actor: int) -> int:
        async with self.factory() as session:
            existing = await session.scalar(
                select(CollaboratorModel.id).where(
                    CollaboratorModel.full_name == "Teste Consultor Escalonado"
                )
            )
            if existing is not None:
                return existing
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
                    full_name="Teste Consultor Escalonado",
                    documento="123.456.789-09",
                    regime=RegimeTributario.MEI,
                    papeis=(
                        PapelSolicitado(
                            papel=PapelDeColaborador.CONSULTOR_MEI_ESCALONADO,
                            valid_from=self.today,
                        ),
                    ),
                    ator=actor,
                )
            )
            return created.id

    async def exists(self, external_id: str) -> bool:
        async with self.factory() as session:
            return (
                await session.scalar(
                    select(ProposalModel.id).where(ProposalModel.external_id == external_id)
                )
                is not None
            )

    async def create_proposal(
        self,
        *,
        context: Contexto,
        consultant_id: int,
        suffix: str,
        customer: str,
        operation: str,
        tps: str,
    ) -> tuple[int, int, str]:
        external_id = f"{PREFIXO}-{suffix}"
        if await self.exists(external_id):
            async with self.factory() as session:
                proposal = await session.scalar(
                    select(ProposalModel).where(ProposalModel.external_id == external_id)
                )
                assert proposal is not None
                return proposal.id, proposal.version, external_id
        async with UnitOfWork(self.factory) as uow:
            created = await CreateProposalHandler(
                uow=uow,
                propostas=SqlProposalRepository(uow.session, self.cipher),
                colaboradores=SqlCollaboratorRepository(uow.session),
                cipher=self.cipher,
                audit=SqlAuditRecorder(uow.session, self.clock),
            ).execute(
                CreateProposal(
                    consultant_id=consultant_id,
                    business_date=self.today,
                    customer_name=customer,
                    customer_document=CPF_CLIENTE,
                    operation_amount=Decimal(operation),
                    tps_percentage=Decimal(tps),
                    external_id=external_id,
                    finalizer_collaborator_id=context.finalizer_id,
                    ator=context.launcher_user_id,
                )
            )
            return created.id, created.version, external_id

    def receipt_service(self, uow: UnitOfWork) -> ReceiptService:
        outbox = SqlOutboxRecorder(uow.session, self.clock)
        return ReceiptService(
            uow=uow,
            proposals=SqlProposalRepository(uow.session, self.cipher),
            storage=self.storage,
            audit=SqlAuditRecorder(uow.session, self.clock),
            outbox=outbox,
            commissions=StandardCommissionEngine(uow.session, outbox),
            contas=SqlReceivingAccountDirectory(uow.session),
            clock=self.clock,
            timezone=self.settings.app.app_timezone,
        )

    async def receipt(
        self,
        *,
        context: Contexto,
        proposal_id: int,
        external_id: str,
        suffix: str,
        amount: str,
    ) -> int:
        async with UnitOfWork(self.factory) as uow:
            result = await self.receipt_service(uow).create(
                proposal_id=proposal_id,
                amount=Decimal(amount),
                business_date=self.today,
                payment_time=None,
                payment_method="PIX",
                receiving_account_id=self.receiving_account_id,
                reference=external_id,
                notes="Massa local de homologação do comissionamento",
                file_name=f"{external_id}.pdf",
                content_type="application/pdf",
                content=COMPROVANTE,
                idempotency_key=f"seed-{external_id}-{suffix}",
                actor=context.launcher_user_id,
                correlation_id=f"seed:{external_id}",
                scope=EscopoDePropostas.total(),
            )
            return result.receipt.id

    async def submit_and_approve(
        self, *, context: Contexto, proposal_id: int, version: int, external_id: str
    ) -> None:
        async with UnitOfWork(self.factory) as uow:
            submitted = await SubmitProposalHandler(
                uow=uow,
                propostas=SqlProposalRepository(uow.session, self.cipher),
                recebimentos=SqlReceiptRecognizer(uow.session, self.clock.now()),
                audit=SqlAuditRecorder(uow.session, self.clock),
                clock=self.clock,
            ).execute(
                SubmitProposal(
                    proposal_id=proposal_id,
                    version=version,
                    ator=context.launcher_user_id,
                    correlation_id=f"seed:{external_id}",
                )
            )
        async with UnitOfWork(self.factory) as uow:
            outbox = SqlOutboxRecorder(uow.session, self.clock)
            await DecideProposalHandler(
                uow=uow,
                propostas=SqlProposalRepository(uow.session, self.cipher),
                recebimentos=SqlReceiptRecognizer(uow.session, self.clock.now()),
                comissoes=StandardCommissionEngine(uow.session, outbox),
                audit=SqlAuditRecorder(uow.session, self.clock),
                outbox=outbox,
                clock=self.clock,
            ).execute(
                DecideProposal(
                    proposal_id=proposal_id,
                    version=submitted.version,
                    decisao=Decisao.APROVAR,
                    ator=context.finance_user_id,
                    correlation_id=f"seed:{external_id}",
                )
            )

    async def approve_receipt(self, context: Contexto, receipt_id: int, external_id: str) -> None:
        async with UnitOfWork(self.factory) as uow:
            await self.receipt_service(uow).decide(
                receipt_id=receipt_id,
                approve=True,
                reason=None,
                actor=context.finance_user_id,
                correlation_id=f"seed:{external_id}",
            )

    async def reverse(
        self, context: Contexto, receipt_id: int, external_id: str, amount: str
    ) -> None:
        async with UnitOfWork(self.factory) as uow:
            await self.receipt_service(uow).reverse(
                receipt_id=receipt_id,
                reason="Estorno controlado do cenário de homologação",
                business_date=self.today,
                amount=Decimal(amount),
                actor=context.finance_user_id,
                correlation_id=f"seed:{external_id}",
            )

    async def approved_scenario(
        self,
        *,
        context: Contexto,
        consultant_id: int,
        suffix: str,
        customer: str,
        operation: str,
        tps: str,
        receipt_amount: str,
    ) -> tuple[int, int, str, bool]:
        existed = await self.exists(f"{PREFIXO}-{suffix}")
        proposal_id, version, external_id = await self.create_proposal(
            context=context,
            consultant_id=consultant_id,
            suffix=suffix,
            customer=customer,
            operation=operation,
            tps=tps,
        )
        if existed:
            return proposal_id, 0, external_id, False
        receipt_id = await self.receipt(
            context=context,
            proposal_id=proposal_id,
            external_id=external_id,
            suffix="inicial",
            amount=receipt_amount,
        )
        await self.submit_and_approve(
            context=context,
            proposal_id=proposal_id,
            version=version,
            external_id=external_id,
        )
        return proposal_id, receipt_id, external_id, True

    async def summary(self) -> None:
        async with self.factory() as session:
            proposals = list(
                (
                    await session.scalars(
                        select(ProposalModel)
                        .where(ProposalModel.external_id.like(f"{PREFIXO}%"))
                        .order_by(ProposalModel.id)
                    )
                ).all()
            )
            print("\nCenários disponíveis na tela de Propostas:")
            for proposal in proposals:
                commission = Decimal(
                    await session.scalar(
                        select(func.coalesce(func.sum(CommissionEntryModel.amount), 0)).where(
                            CommissionEntryModel.proposal_id == proposal.id
                        )
                    )
                    or 0
                )
                calculations = int(
                    await session.scalar(
                        select(func.count(CommissionCalculationSnapshotModel.id)).where(
                            CommissionCalculationSnapshotModel.proposal_id == proposal.id
                        )
                    )
                    or 0
                )
                pending = int(
                    await session.scalar(
                        select(func.count(ReceiptModel.id)).where(
                            ReceiptModel.proposal_id == proposal.id,
                            ReceiptModel.status == "SUBMITTED",
                        )
                    )
                    or 0
                )
                print(
                    f"  #{proposal.id:<4} {proposal.external_id:<48} "
                    f"{proposal.status:<15} recebido={proposal.paid_amount_cached:>10} "
                    f"comissões={commission:>10} cálculos={calculations} pendentes={pending}"
                )

    async def validate(self) -> None:
        expected = {
            "TPS-24-99": (Decimal("2499.00"), Decimal("149.94"), 0),
            "TPS-25-PARCIAL": (Decimal("1250.00"), Decimal("100.00"), 0),
            "TPS-35-EXCEDENTE": (Decimal("3500.00"), Decimal("420.00"), 0),
            "ESCALONADO-75K": (Decimal("26250.00"), Decimal("2100.00"), 0),
            "ESCALONADO-CRUZA": (Decimal("7000.00"), Decimal("700.00"), 0),
            "ESTORNO-SUBSTITUTO": (Decimal("1000.00"), Decimal("60.00"), 0),
            "RECEBIMENTO-PENDENTE": (Decimal("200.00"), Decimal("12.00"), 1),
        }
        async with self.factory() as session:
            count = int(
                await session.scalar(
                    select(func.count(ProposalModel.id)).where(
                        ProposalModel.external_id.like(f"{PREFIXO}%")
                    )
                )
                or 0
            )
            if count != len(expected):
                raise RuntimeError(
                    f"Esperadas {len(expected)} propostas de teste; encontradas {count}."
                )
            for suffix, (paid, commission, pending) in expected.items():
                proposal = await session.scalar(
                    select(ProposalModel).where(ProposalModel.external_id == f"{PREFIXO}-{suffix}")
                )
                assert proposal is not None
                actual_commission = Decimal(
                    await session.scalar(
                        select(func.coalesce(func.sum(CommissionEntryModel.amount), 0))
                        .join(
                            CommissionCalculationSnapshotModel,
                            CommissionCalculationSnapshotModel.id
                            == CommissionEntryModel.snapshot_id,
                        )
                        .where(
                            CommissionEntryModel.proposal_id == proposal.id,
                            CommissionCalculationSnapshotModel.strategy.in_(
                                ("STANDARD_CONSULTANT", "SCALED_CONSULTANT")
                            ),
                        )
                    )
                    or 0
                )
                actual_pending = int(
                    await session.scalar(
                        select(func.count(ReceiptModel.id)).where(
                            ReceiptModel.proposal_id == proposal.id,
                            ReceiptModel.status == "SUBMITTED",
                        )
                    )
                    or 0
                )
                actual = (Decimal(proposal.paid_amount_cached), actual_commission, actual_pending)
                if actual != (paid, commission, pending):
                    raise RuntimeError(
                        f"Cenário {suffix} divergiu: atual={actual}, "
                        f"esperado={(paid, commission, pending)}"
                    )


async def execute() -> int:
    populator = Populador()
    if populator.settings.app.is_production:
        print("seed de comissionamento não roda em produção", file=sys.stderr)
        return 1
    try:
        # a conta é obrigatória no lançamento; a massa cria a sua e a reaproveita
        populator.receiving_account_id = await populator.conta_de_recebimento()
        context, scaled_id = await populator.context()
        scenarios = (
            (context.consultant_id, "TPS-24-99", "Teste faixa TPS 24,99", "10000", "24.99", "2499"),
            (
                context.consultant_id,
                "TPS-25-PARCIAL",
                "Teste TPS 25 parcial",
                "10000",
                "25",
                "1250",
            ),
            (
                context.consultant_id,
                "TPS-35-EXCEDENTE",
                "Teste TPS 35 excedente",
                "10000",
                "35",
                "3550",
            ),
            (scaled_id, "ESCALONADO-75K", "Teste escalonado até 75 mil", "75000", "35", "26250"),
            (scaled_id, "ESCALONADO-CRUZA", "Teste escalonado cruza faixa", "20000", "35", "7000"),
            (
                context.consultant_id,
                "ESTORNO-SUBSTITUTO",
                "Teste estorno e substituição",
                "10000",
                "10",
                "1000",
            ),
            (
                context.consultant_id,
                "RECEBIMENTO-PENDENTE",
                "Teste recebimento pendente",
                "10000",
                "10",
                "200",
            ),
        )
        created: dict[str, tuple[int, int, str, bool]] = {}
        for consultant_id, suffix, customer, operation, tps, amount in scenarios:
            created[suffix] = await populator.approved_scenario(
                context=context,
                consultant_id=consultant_id,
                suffix=suffix,
                customer=customer,
                operation=operation,
                tps=tps,
                receipt_amount=amount,
            )

        overpayment = created["TPS-35-EXCEDENTE"]
        if overpayment[3]:
            await populator.reverse(context, overpayment[1], overpayment[2], "50")

        replacement = created["ESTORNO-SUBSTITUTO"]
        if replacement[3]:
            await populator.reverse(context, replacement[1], replacement[2], "500")
            replacement_receipt = await populator.receipt(
                context=context,
                proposal_id=replacement[0],
                external_id=replacement[2],
                suffix="substituto",
                amount="500",
            )
            await populator.approve_receipt(context, replacement_receipt, replacement[2])

        pending = created["RECEBIMENTO-PENDENTE"]
        if pending[3]:
            await populator.receipt(
                context=context,
                proposal_id=pending[0],
                external_id=pending[2],
                suffix="aguardando-financeiro",
                amount="300",
            )

        await populator.validate()
        await populator.summary()
        print("\nValidação automática: 7 de 7 cenários conferidos com sucesso.")
        print(f"\nFiltro sugerido: ID externo começando por {PREFIXO}")
        return 0
    finally:
        await populator.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(execute()))
