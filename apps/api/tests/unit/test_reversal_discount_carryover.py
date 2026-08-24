from datetime import date
from decimal import Decimal

from app.modules.commissions.application.manage_settlements import CommissionSettlementManager
from app.modules.commissions.infrastructure.models.commission_models import (
    CommissionSettlementModel,
)


def _settlement(*, gross: str, debt: str) -> CommissionSettlementModel:
    return CommissionSettlementModel(
        beneficiary_id=1,
        period_start=date(2026, 8, 14),
        period_end=date(2026, 8, 20),
        gross_amount=Decimal(gross),
        carryover_amount=Decimal("0.00"),
        bonus_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        manual_discount_amount=Decimal("0.00"),
        reversal_discount_amount=Decimal("0.00"),
        reversal_carryover_amount=Decimal(debt),
        deferred_amount=Decimal("0.00"),
        paid_amount=Decimal("0.00"),
        payable_amount=Decimal("0.00"),
        status="PENDING",
        created_by=1,
        updated_by=1,
    )


def test_estorno_vira_desconto_e_carrega_o_restante_para_as_proximas_semanas() -> None:
    first_week = _settlement(gross="30.00", debt="100.00")
    CommissionSettlementManager._apply_reversal_discount(first_week)
    CommissionSettlementManager._recalculate(first_week)
    assert first_week.reversal_discount_amount == Decimal("30.00")
    assert first_week.reversal_carryover_amount == Decimal("70.00")
    assert first_week.payable_amount == Decimal("0.00")

    second_week = _settlement(gross="50.00", debt=str(first_week.reversal_carryover_amount))
    CommissionSettlementManager._apply_reversal_discount(second_week)
    CommissionSettlementManager._recalculate(second_week)
    assert second_week.reversal_discount_amount == Decimal("50.00")
    assert second_week.reversal_carryover_amount == Decimal("20.00")

    third_week = _settlement(gross="25.00", debt=str(second_week.reversal_carryover_amount))
    CommissionSettlementManager._apply_reversal_discount(third_week)
    CommissionSettlementManager._recalculate(third_week)
    assert third_week.reversal_discount_amount == Decimal("20.00")
    assert third_week.reversal_carryover_amount == Decimal("0.00")
    assert third_week.payable_amount == Decimal("5.00")
