import { useQuery } from '@tanstack/react-query';

import type { Period } from '@/features/settlements/queries/useSettlements';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { FinancialReport, FinancialReportDetailPage } from '@/shared/types/commissions';

function params(period: Period): string {
  return new URLSearchParams({
    period_start: period.period_start,
    period_end: period.period_end,
  }).toString();
}

export function useFinancialReport(period: Period) {
  return useQuery<FinancialReport, ApiError>({
    queryKey: ['commission-financial-report', period],
    queryFn: ({ signal }) => requisitar(`/commission-financial-report?${params(period)}`, { signal }),
    enabled: Boolean(period.period_start && period.period_end),
  });
}

export function useFinancialReportDetails(beneficiaryId: number | null, period: Period) {
  return useQuery<FinancialReportDetailPage, ApiError>({
    queryKey: ['commission-financial-report', 'beneficiary', beneficiaryId, period],
    queryFn: ({ signal }) => requisitar(
      `/commission-financial-report/beneficiaries/${beneficiaryId}?${params(period)}`,
      { signal },
    ),
    enabled: beneficiaryId !== null,
  });
}
