from datetime import date

from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    proposal_count: int
    open_count: int
    partially_paid_count: int
    paid_count: int
    cancelled_count: int
    pending_approval_count: int
    approved_production: str
    company_commission: str
    recognized_revenue: str
    total_commissions: str
    net_revenue: str
    outstanding_amount: str
    average_tps: str


class DashboardTrendResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    business_date: date
    proposal_count: int
    production_amount: str
    recognized_revenue: str


class DashboardRankingResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    collaborator_id: int
    collaborator_name: str
    proposal_count: int
    production_amount: str


class DashboardResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    period_start: date
    period_end: date
    summary: DashboardSummaryResponse
    trend: list[DashboardTrendResponse]
    ranking: list[DashboardRankingResponse]
