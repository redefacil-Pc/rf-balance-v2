export interface DashboardSummary {
  proposal_count: number;
  open_count: number;
  partially_paid_count: number;
  paid_count: number;
  cancelled_count: number;
  pending_approval_count: number;
  approved_production: string;
  company_commission: string;
  recognized_revenue: string;
  total_commissions: string;
  net_revenue: string;
  outstanding_amount: string;
  average_tps: string;
}

export interface DashboardTrend {
  business_date: string;
  proposal_count: number;
  production_amount: string;
  recognized_revenue: string;
}

export interface DashboardRanking {
  collaborator_id: number;
  collaborator_name: string;
  proposal_count: number;
  production_amount: string;
}

export interface DashboardData {
  period_start: string;
  period_end: string;
  summary: DashboardSummary;
  trend: DashboardTrend[];
  ranking: DashboardRanking[];
}
