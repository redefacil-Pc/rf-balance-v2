import { useQuery } from '@tanstack/react-query';

import type { DashboardData } from '@/features/dashboard/types';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export interface DashboardPeriod {
  period_start: string;
  period_end: string;
}

export function useDashboard(period: DashboardPeriod) {
  const params = new URLSearchParams({
    period_start: period.period_start,
    period_end: period.period_end,
  }).toString();
  return useQuery<DashboardData, ApiError>({
    queryKey: ['dashboard', period],
    queryFn: ({ signal }) => requisitar<DashboardData>(`/dashboard?${params}`, { signal }),
    enabled: Boolean(period.period_start && period.period_end),
  });
}
