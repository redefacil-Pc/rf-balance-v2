from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.platform.db.validate_golden_cases import (
    GoldenCase,
    proposal_status,
    recognized_amount,
)


def _case(*, status: str = "CONFIRMED", received: str = "1000", reversal: str = "0") -> GoldenCase:
    return GoldenCase(
        case_id="CASE-1",
        category="STANDARD",
        competence_date=date(2026, 8, 1),
        consultant_profile="CONSULTOR",
        operation_amount=Decimal("10000.00"),
        received_amount=Decimal(received),
        tps_percent=Decimal("25.00"),
        prior_month_production=Decimal("0.00"),
        receipt_status=status,
        reversal_amount=Decimal(reversal),
        leader_profile="NONE",
        expected_consultant=Decimal("0.00"),
        expected_leadership=Decimal("0.00"),
        expected_finalization=Decimal("0.00"),
        expected_bko=Decimal("0.00"),
        expected_total=Decimal("0.00"),
        expected_status="OPEN",
    )


def test_recebimento_pendente_nao_e_reconhecido() -> None:
    assert recognized_amount(_case(status="SUBMITTED", received="2500")) == Decimal("0.00")


def test_estorno_e_substituto_usam_valor_liquido() -> None:
    assert recognized_amount(_case(received="2000", reversal="1000")) == Decimal("1000.00")


def test_status_respeita_limites_inclusivos_da_tolerancia_v1() -> None:
    assert proposal_status(
        company_commission=Decimal("3500"), received=Decimal("3490")
    ) == "PAID"
    assert proposal_status(
        company_commission=Decimal("3500"), received=Decimal("3489.99")
    ) == "PARTIALLY_PAID"
    assert proposal_status(
        company_commission=Decimal("3500"), received=Decimal("3600")
    ) == "PAID"
