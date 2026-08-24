"""Gera massa sintética de três anos para os gates de performance.

Uso no banco de testes:

    python -m app.platform.db.seed_volumetric --proposals 20000 --reset
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, insert, select, text

from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionCalculationSnapshotModel,
    CommissionEntryModel,
)
from app.modules.identity.infrastructure import seed_identity
from app.modules.organization.infrastructure.models.collaborator_model import CollaboratorModel
from app.modules.organization.infrastructure.models.collaborator_role_model import (
    CollaboratorRoleModel,
)
from app.modules.organization.infrastructure.models.company_model import CompanyModel
from app.modules.organization.infrastructure.models.receiving_account_model import (
    ReceivingAccountModel,
)
from app.modules.organization.infrastructure.models.unit_model import UnitModel
from app.modules.receivables.infrastructure.models.receipt_model import ReceiptModel
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes

START_DATE = date(2023, 1, 1)
DAYS = 365 * 3
BATCH_SIZE = 1000
PERFORMANCE_PASSWORD = "performance-ci-password-2026"

_VOLUME_TABLES = (
    "commission_entries",
    "commission_calculation_snapshots",
    "receipts",
    "proposals",
    "collaborator_roles",
    "collaborators",
    "units",
    "companies",
    "receiving_accounts",
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _insert_batches(connection: Any, model: Any, rows: list[dict[str, Any]]) -> None:
    for start in range(0, len(rows), BATCH_SIZE):
        await connection.execute(insert(model), rows[start : start + BATCH_SIZE])


async def _reset(connection: Any) -> None:
    await connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    for table in _VOLUME_TABLES:
        await connection.execute(text(f"TRUNCATE TABLE {table}"))
    await connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


async def seed_volumetric(*, proposal_count: int, reset: bool) -> dict[str, int]:
    settings = get_settings()
    if settings.app.is_production:
        raise RuntimeError("seed volumétrico não roda em produção")
    if proposal_count < 1000 or proposal_count > 1_000_000:
        raise ValueError("--proposals deve ficar entre 1.000 e 1.000.000")

    engine = criar_engine(settings.database)
    factory = criar_fabrica_de_sessoes(engine)
    try:
        async with engine.begin() as connection:
            if reset:
                await _reset(connection)
            existing = int(
                await connection.scalar(select(func.count(ProposalModel.id))) or 0
            )
            if existing:
                raise RuntimeError("já existem propostas; use --reset em um banco descartável")

        os.environ.setdefault("SEED_ADMIN_PASSWORD", PERFORMANCE_PASSWORD)
        async with factory() as session:
            await seed_identity.semear(session)
            await session.commit()
            admin_id = int(
                await session.scalar(
                    text("SELECT id FROM users WHERE email='admin@rfbalance.local'")
                )
                or 0
            )
        if not admin_id:
            raise RuntimeError("administrador do cenário não foi criado")

        now = datetime.now(UTC)
        companies = [
            {
                "id": company_id,
                "legal_name": f"Empresa Performance {company_id}",
                "trade_name": f"Perf {company_id}",
                "is_active": True,
                "created_by": admin_id,
            }
            for company_id in range(1, 6)
        ]
        units = [
            {
                "id": unit_id,
                "company_id": ((unit_id - 1) % 5) + 1,
                "code": f"U{unit_id:02d}",
                "name": f"Unidade Performance {unit_id:02d}",
                "is_active": True,
                "created_by": admin_id,
            }
            for unit_id in range(1, 11)
        ]
        collaborators = [
            {
                "id": collaborator_id,
                "company_id": ((collaborator_id - 1) % 5) + 1,
                "unit_id": ((collaborator_id - 1) % 10) + 1,
                "full_name": f"Consultor Performance {collaborator_id:03d}",
                "document_encrypted": f"synthetic:{collaborator_id}",
                "document_hash": _hash(f"collaborator:{collaborator_id}"),
                "document_type": "CPF",
                "tax_regime": "MEI" if collaborator_id % 2 else "CLT",
                "email": f"perf{collaborator_id:03d}@example.invalid",
                "is_active": True,
                "created_by": admin_id,
                "version": 1,
            }
            for collaborator_id in range(1, 101)
        ]
        roles = [
            {
                "id": collaborator_id,
                "collaborator_id": collaborator_id,
                "role": "CONSULTOR",
                "valid_from": START_DATE,
                "created_by": admin_id,
            }
            for collaborator_id in range(1, 101)
        ]
        proposals: list[dict[str, Any]] = []
        receipts: list[dict[str, Any]] = []
        snapshots: list[dict[str, Any]] = []
        entries: list[dict[str, Any]] = []
        approved_count = 0
        for proposal_id in range(1, proposal_count + 1):
            business_date = START_DATE + timedelta(days=(proposal_id - 1) % DAYS)
            consultant_id = ((proposal_id - 1) % 100) + 1
            operation_amount = Decimal(10_000 + (proposal_id % 400) * 100)
            tps = Decimal(25 + proposal_id % 16)
            company_commission = (operation_amount * tps / 100).quantize(Decimal("0.01"))
            approved = proposal_id % 10 != 0
            proposals.append(
                {
                    "id": proposal_id,
                    "external_id": f"PERF-{proposal_id:07d}",
                    "consultant_id": consultant_id,
                    "business_date": business_date,
                    "customer_name": f"Cliente Sintético {proposal_id:07d}",
                    "customer_document_encrypted": f"synthetic-customer:{proposal_id % 5000}",
                    "customer_document_hash": _hash(f"customer:{proposal_id % 5000}"),
                    "customer_document_type": "CPF",
                    "operation_amount": operation_amount,
                    "tps_percentage": tps,
                    "company_commission_amount": company_commission,
                    "paid_amount_cached": company_commission if approved else Decimal("0.00"),
                    "outstanding_amount_cached": (
                        Decimal("0.00") if approved else company_commission
                    ),
                    "status": "PAID" if approved else "OPEN",
                    "approval_status": "APPROVED" if approved else "SUBMITTED",
                    "submitted_at": now,
                    "submitted_by": admin_id,
                    "decided_at": now if approved else None,
                    "decided_by": admin_id if approved else None,
                    "tolerance_policy_version": "v1",
                    "created_by": admin_id,
                    "updated_by": admin_id,
                    "version": 1,
                }
            )
            if not approved:
                continue
            approved_count += 1
            receipt_id = approved_count
            inputs = {
                "receipt_eligible_amount": str(company_commission),
                "company_commission": str(company_commission),
                "tps": str(tps),
            }
            outputs = {"recognized_production": str(operation_amount)}
            receipts.append(
                {
                    "id": receipt_id,
                    "proposal_id": proposal_id,
                    "amount": company_commission,
                    "business_date": business_date,
                    "payment_datetime": now,
                    "payment_method": "PIX",
                    "receiving_account_id": 1,
                    "status": "APPROVED",
                    "proof_file_name": f"perf-{receipt_id}.pdf",
                    "proof_content_type": "application/pdf",
                    "proof_size_bytes": 128,
                    "proof_storage_key": f"performance/{receipt_id}.pdf",
                    "proof_sha256": _hash(f"proof:{receipt_id}"),
                    "idempotency_key": f"performance-{receipt_id}",
                    "request_hash": _hash(f"request:{receipt_id}"),
                    "created_by": admin_id,
                    "decided_at": now,
                    "decided_by": admin_id,
                }
            )
            snapshots.append(
                {
                    "id": receipt_id,
                    "proposal_id": proposal_id,
                    "receipt_id": receipt_id,
                    "beneficiary_id": consultant_id,
                    "strategy": "STANDARD_CONSULTANT",
                    "competence_date": business_date,
                    "inputs": inputs,
                    "outputs": outputs,
                    "input_hash": _hash(f"snapshot:{receipt_id}"),
                }
            )
            entries.append(
                {
                    "id": receipt_id,
                    "snapshot_id": receipt_id,
                    "proposal_id": proposal_id,
                    "receipt_id": receipt_id,
                    "beneficiary_id": consultant_id,
                    "entry_type": "CREDIT",
                    "amount": (company_commission * Decimal("0.05")).quantize(Decimal("0.01")),
                    "competence_date": business_date,
                    "description": "Comissão sintética para teste de performance",
                }
            )

        async with engine.begin() as connection:
            await connection.execute(insert(CompanyModel), companies)
            await connection.execute(insert(UnitModel), units)
            await connection.execute(insert(ReceivingAccountModel), [{
                "id": 1, "label": "Conta Performance", "display_order": 1,
                "is_active": True, "created_by": admin_id,
            }])
            await _insert_batches(connection, CollaboratorModel, collaborators)
            await _insert_batches(connection, CollaboratorRoleModel, roles)
            await _insert_batches(connection, ProposalModel, proposals)
            await _insert_batches(connection, ReceiptModel, receipts)
            await _insert_batches(connection, CommissionCalculationSnapshotModel, snapshots)
            await _insert_batches(connection, CommissionEntryModel, entries)
        return {
            "companies": len(companies),
            "units": len(units),
            "collaborators": len(collaborators),
            "proposals": len(proposals),
            "receipts": len(receipts),
            "commission_entries": len(entries),
        }
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=int, default=50_000)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    try:
        result = asyncio.run(seed_volumetric(proposal_count=args.proposals, reset=args.reset))
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(" ".join(f"{key}={value}" for key, value in result.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
