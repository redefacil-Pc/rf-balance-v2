import { useQuery } from '@tanstack/react-query';

import type { Period } from '@/features/settlements/queries/useSettlements';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { FinancialReport, FinancialReportDetailPage } from '@/shared/types/commissions';

export interface FinancialReportScope {
  unit_id?: number;
  leader_id?: number;
}

export function financialReportParams(period: Period, scope: FinancialReportScope = {}): string {
  const query = new URLSearchParams({
    period_start: period.period_start,
    period_end: period.period_end,
  });
  if (scope.unit_id) query.set('unit_id', String(scope.unit_id));
  if (scope.leader_id) query.set('leader_id', String(scope.leader_id));
  return query.toString();
}

export function useFinancialReport(period: Period, scope: FinancialReportScope = {}) {
  return useQuery<FinancialReport, ApiError>({
    queryKey: ['commission-financial-report', period, scope],
    queryFn: ({ signal }) => requisitar(
      `/commission-financial-report?${financialReportParams(period, scope)}`,
      { signal },
    ),
    enabled: Boolean(period.period_start && period.period_end),
  });
}

export function useFinancialReportDetails(
  beneficiaryId: number | null,
  period: Period,
  scope: FinancialReportScope = {},
) {
  return useQuery<FinancialReportDetailPage, ApiError>({
    queryKey: ['commission-financial-report', 'beneficiary', beneficiaryId, period, scope],
    queryFn: ({ signal }) => requisitar(
      `/commission-financial-report/beneficiaries/${beneficiaryId}?${financialReportParams(period, scope)}`,
      { signal },
    ),
    enabled: beneficiaryId !== null,
  });
}
