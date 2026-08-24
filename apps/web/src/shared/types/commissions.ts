export type TaxRegime = 'MEI';
export type CommissionRuleStatus = 'ACTIVE' | 'DRAFT' | 'RETIRED';

export interface CommissionBandInput {
  tax_regime: TaxRegime;
  tps_min: string;
  tps_max: string | null;
  percentage: string;
}

export interface CommissionBand extends CommissionBandInput {
  id: number;
  sort_order: number;
}

export interface CommissionRuleSet {
  id: number;
  strategy: 'STANDARD_CONSULTANT';
  version: string;
  name: string;
  status: CommissionRuleStatus;
  valid_from: string;
  valid_to: string | null;
  reason: string;
  created_at: string;
  created_by: number | null;
  activated_at: string | null;
  activated_by: number | null;
  rules: CommissionBand[];
}

export interface CommissionRuleSetInput {
  version: string;
  name: string;
  valid_from: string;
  reason: string;
  rules: CommissionBandInput[];
}

export type CommissionStrategy =
  | 'SCALED_CONSULTANT'
  | 'COMMERCIAL_LEADER'
  | 'GENERAL_MEI_LEADER'
  | 'FINALIZER'
  | 'FINALIZATION_LEADER';

export interface ProductionRange {
  min: string;
  max: string | null;
  percentages: string[];
}

export interface TpsRange {
  min: string;
  max: string | null;
}

export interface LeaderTier {
  min: string;
  max: string;
  percentage: string;
}

export interface CommissionStrategyPayload {
  display_mode?: 'WEEKLY' | 'MONTHLY';
  production_ranges?: ProductionRange[];
  tps_ranges?: TpsRange[];
  mei_min_tps?: string;
  mei_percentage?: string;
  clt_percentage?: string;
  base_percentage?: string;
  tiers?: LeaderTier[];
  threshold_amount?: string;
  fixed_amount?: string;
  excess_percentage?: string;
}

export interface CommissionStrategyConfig {
  id: number;
  strategy: CommissionStrategy;
  version: string;
  name: string;
  status: 'ACTIVE' | 'DRAFT';
  valid_from: string;
  valid_to: string | null;
  config: CommissionStrategyPayload;
  reason: string;
  created_at: string;
  created_by: number | null;
  activated_at: string | null;
  activated_by: number | null;
}

export interface CommissionStrategyConfigInput {
  strategy: CommissionStrategy;
  version: string;
  name: string;
  valid_from: string;
  reason: string;
  config: CommissionStrategyPayload;
}

export interface CommissionBeneficiaryPolicy {
  id: number;
  collaborator_id: number;
  collaborator_name: string;
  valid_from: string;
  valid_to: string | null;
  excluded: boolean;
  override_tps_35_percentage: string | null;
  reason: string;
}

export interface CommissionSettlement {
  id: number;
  beneficiary_id: number;
  beneficiary_name: string;
  roles: string[];
  period_start: string;
  period_end: string;
  gross_amount: string;
  carryover_amount: string;
  bonus_amount: string;
  discount_amount: string;
  manual_discount_amount: string;
  reversal_discount_amount: string;
  reversal_carryover_amount: string;
  deferred_amount: string;
  paid_amount: string;
  payable_amount: string;
  status: 'PENDING' | 'DEFERRED' | 'PAID';
  payment_date: string | null;
  payment_method: string | null;
  payment_reference: string | null;
  notes: string | null;
  created_at: string;
}

export interface CommissionSettlementPage {
  items: CommissionSettlement[];
}

export interface CommissionPeriod {
  id: number;
  period_start: string;
  period_end: string;
  cutoff_at: string;
  status: 'OPEN' | 'CLOSED' | 'REOPENING_PENDING';
  reason: string;
  created_at: string;
  created_by: number;
  closed_at: string | null;
  closed_by: number | null;
  reopened_at: string | null;
  reopened_by: number | null;
  reopen_requested_at: string | null;
  reopen_requested_by: number | null;
  reopen_reason: string | null;
}

export interface FinancialReportSummary {
  gross_revenue: string;
  receipt_reversals: string;
  recognized_revenue: string;
  recognized_production: string;
  consultant_commissions: string;
  leader_commissions: string;
  finalization_commissions: string;
  finalization_leader_commissions: string;
  bko_commissions: string;
  total_commissions: string;
  net_billing: string;
  bonuses: string;
  discounts: string;
  deferred: string;
  paid: string;
  payable: string;
}

export interface FinancialReportBeneficiary {
  beneficiary_id: number;
  beneficiary_name: string;
  strategies: string[];
  automatic_amount: string;
  manual_amount: string;
  calculated_amount: string;
  carryover_amount: string;
  bonus_amount: string;
  discount_amount: string;
  deferred_amount: string;
  paid_amount: string;
  payable_amount: string;
  status: 'PENDING' | 'DEFERRED' | 'PAID' | null;
}

export interface FinancialReport {
  period_start: string;
  period_end: string;
  summary: FinancialReportSummary;
  beneficiaries: FinancialReportBeneficiary[];
}

export interface FinancialReportDetail {
  source: 'AUTOMATIC' | 'MANUAL';
  strategy: string;
  entry_type: string;
  competence_date: string;
  amount: string;
  description: string;
  proposal_id: number | null;
  proposal_external_id: string | null;
  customer_name: string | null;
  receipt_id: number | null;
  recognized_production: string;
  received_amount: string;
  received_percentage: string | null;
  tps_percentage: string | null;
}

export interface FinancialReportDetailPage {
  summary: {
    recognized_production: string;
    received_amount: string;
    commission_amount: string;
    deferred_amount: string;
  };
  items: FinancialReportDetail[];
}
