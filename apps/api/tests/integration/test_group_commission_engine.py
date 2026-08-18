from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commissions.application.standard_commission_engine import StandardCommissionEngine
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionBeneficiaryPolicyModel,
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
)
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.models.collaborator_role_model import (
    CollaboratorRoleModel,
)
from app.modules.organization.infrastructure.models.company_model import CompanyModel
from app.modules.receivables.infrastructure.models.receipt_model import (
    ReceiptModel,
    ReceiptReversalModel,
)
from app.modules.teams.infrastructure.models.team_assignment_model import TeamAssignmentModel
from app.platform.bus.outbox_recorder import SqlOutboxRecorder
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.time.clock import FrozenClock

pytestmark = pytest.mark.integration


async def test_motores_automaticos_geram_creditos_e_debitos_explicaveis() -> None:
    engine = criar_engine(get_settings().database)
    fabrica = criar_fabrica_de_sessoes(engine)
    clock = FrozenClock(datetime(2026, 8, 17, 15, tzinfo=UTC))
    try:
        async with fabrica() as session:
            company = CompanyModel(legal_name="Grupo Teste", trade_name="Grupo Teste")
            session.add(company)
            await session.flush()

            def collaborator(name: str, document: str, regime: str = "MEI") -> CollaboratorModel:
                item = CollaboratorModel(
                    company_id=company.id,
                    full_name=name,
                    document_encrypted=document,
                    document_hash=document,
                    document_type="CPF",
                    tax_regime=regime,
                    is_active=True,
                )
                session.add(item)
                return item

            consultant = collaborator("Consultora", "doc-consultant")
            commercial_leader = collaborator("Líder Comercial", "doc-commercial")
            general_leader = collaborator("Líder Geral", "doc-general")
            finalizer = collaborator("Finalizadora", "doc-finalizer", "CLT")
            finalization_leader = collaborator("Líder Finalização", "doc-final-leader")
            await session.flush()
            session.add_all(
                [
                    CollaboratorRoleModel(
                        collaborator_id=consultant.id,
                        role="CONSULTOR",
                        valid_from=date(2026, 1, 1),
                    ),
                    CollaboratorRoleModel(
                        collaborator_id=commercial_leader.id,
                        role="LIDER",
                        valid_from=date(2026, 1, 1),
                    ),
                    CollaboratorRoleModel(
                        collaborator_id=general_leader.id,
                        role="LIDER_MEI_GERAL",
                        valid_from=date(2026, 1, 1),
                    ),
                    CollaboratorRoleModel(
                        collaborator_id=finalizer.id,
                        role="FINALIZACAO",
                        valid_from=date(2026, 1, 1),
                    ),
                    CollaboratorRoleModel(
                        collaborator_id=finalization_leader.id,
                        role="LIDER_FINALIZACAO",
                        valid_from=date(2026, 1, 1),
                    ),
                    TeamAssignmentModel(
                        consultant_id=consultant.id,
                        leader_id=commercial_leader.id,
                        assignment_type="COMERCIAL",
                        start_date=date(2026, 1, 1),
                    ),
                    TeamAssignmentModel(
                        consultant_id=consultant.id,
                        leader_id=general_leader.id,
                        assignment_type="MEI_GERAL",
                        start_date=date(2026, 1, 1),
                    ),
                    TeamAssignmentModel(
                        consultant_id=finalizer.id,
                        leader_id=finalization_leader.id,
                        assignment_type="FINALIZACAO",
                        start_date=date(2026, 1, 1),
                    ),
                ]
            )
            session.add(
                CommissionBeneficiaryPolicyModel(
                    collaborator_id=consultant.id,
                    valid_from=date(2026, 1, 1),
                    excluded=False,
                    override_tps_35_percentage=Decimal("13.5"),
                    reason="Override de teste",
                    created_by=1,
                )
            )
            proposal = ProposalModel(
                consultant_id=consultant.id,
                finalizer_collaborator_id=finalizer.id,
                business_date=date(2026, 8, 14),
                customer_name="Cliente",
                customer_document_encrypted="cliente",
                customer_document_hash="cliente-hash",
                customer_document_type="CPF",
                operation_amount=Decimal("100000.00"),
                tps_percentage=Decimal("35"),
                company_commission_amount=Decimal("35000.00"),
                paid_amount_cached=Decimal("12000.00"),
                outstanding_amount_cached=Decimal("23000.00"),
                status="PARTIALLY_PAID",
                approval_status="APPROVED",
                tolerance_policy_version="v1",
                version=1,
            )
            session.add(proposal)
            await session.flush()
            receipt = ReceiptModel(
                proposal_id=proposal.id,
                amount=Decimal("12000.00"),
                business_date=date(2026, 8, 14),
                payment_method="PIX",
                status="APPROVED",
                proof_file_name="proof.pdf",
                proof_content_type="application/pdf",
                proof_size_bytes=1,
                proof_storage_key="group-test-proof",
                proof_sha256="0" * 64,
                idempotency_key="group-test-receipt",
                request_hash="1" * 64,
                created_by=1,
            )
            session.add(receipt)
            await session.flush()
            commissions = StandardCommissionEngine(session, SqlOutboxRecorder(session, clock))
            await commissions.gerar_para_proposta(proposal.id, correlation_id="group-test")

            credits = dict(
                (
                    await session.execute(
                        select(
                            CommissionCalculationSnapshotModel.strategy,
                            CommissionEntryModel.amount,
                        )
                        .join(
                            CommissionEntryModel,
                            CommissionEntryModel.snapshot_id
                            == CommissionCalculationSnapshotModel.id,
                        )
                        .where(CommissionEntryModel.entry_type == "CREDIT")
                    )
                ).all()
            )
            assert credits == {
                "STANDARD_CONSULTANT": Decimal("1620.00"),
                "COMMERCIAL_LEADER": Decimal("360.00"),
                "GENERAL_MEI_LEADER": Decimal("144.00"),
                "FINALIZER": Decimal("0.00"),
                "FINALIZATION_LEADER": Decimal("108.00"),
            }

            reversal = ReceiptReversalModel(
                receipt_id=receipt.id,
                proposal_id=proposal.id,
                amount=Decimal("6000.00"),
                reason="Correção",
                business_date=date(2026, 8, 17),
                created_by=1,
            )
            session.add(reversal)
            await session.flush()
            await commissions.estornar(reversal.id, correlation_id="group-reversal")
            debits = dict(
                (
                    await session.execute(
                        select(
                            CommissionCalculationSnapshotModel.strategy,
                            CommissionEntryModel.amount,
                        )
                        .join(
                            CommissionEntryModel,
                            CommissionEntryModel.snapshot_id
                            == CommissionCalculationSnapshotModel.id,
                        )
                        .where(CommissionEntryModel.entry_type == "DEBIT")
                    )
                ).all()
            )
            assert debits == {
                "STANDARD_CONSULTANT": Decimal("-810.00"),
                "COMMERCIAL_LEADER": Decimal("-180.00"),
                "GENERAL_MEI_LEADER": Decimal("-72.00"),
                "FINALIZATION_LEADER": Decimal("-54.00"),
            }
            await session.rollback()
    finally:
        await engine.dispose()
