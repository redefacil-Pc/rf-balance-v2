from datetime import date

from pydantic import BaseModel, ConfigDict


class FinancialReportSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    gross_revenue: str
    receipt_reversals: str
    recognized_revenue: str
    recognized_production: str
    consultant_commissions: str
    leader_commissions: str
    finalization_commissions: str
    finalization_leader_commissions: str
    bko_commissions: str
    total_commissions: str
    net_billing: str
    bonuses: str
    discounts: str
    deferred: str
    paid: str
    payable: str


class FinancialReportBeneficiaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    beneficiary_id: int
    beneficiary_name: str
    strategies: list[str]
    automatic_amount: str
    manual_amount: str
    calculated_amount: str
    carryover_amount: str
    bonus_amount: str
    discount_amount: str
    deferred_amount: str
    paid_amount: str
    payable_amount: str
    status: str | None


class FinancialReportResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    period_start: date
    period_end: date
    summary: FinancialReportSummaryResponse
    beneficiaries: list[FinancialReportBeneficiaryResponse]


class FinancialReportDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: str
    strategy: str
    entry_type: str
    competence_date: date
    amount: str
    description: str
    proposal_id: int | None
    proposal_external_id: str | None
    customer_name: str | None
    receipt_id: int | None
    recognized_production: str
    received_amount: str
    received_percentage: str | None
    tps_percentage: str | None


class FinancialReportDetailSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    recognized_production: str
    received_amount: str
    commission_amount: str
    deferred_amount: str


class FinancialReportDetailPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    summary: FinancialReportDetailSummaryResponse
    items: list[FinancialReportDetailResponse]
