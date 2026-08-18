import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CommissionPeriod } from '@/shared/types/commissions';

const key = ['commission-periods'] as const;

export function useCommissionPeriods() {
  return useQuery<CommissionPeriod[], ApiError>({
    queryKey: key,
    queryFn: ({ signal }) => requisitar('/commission-periods', { signal }),
  });
}

export function useCreateCommissionPeriod() {
  const client = useQueryClient();
  return useMutation<CommissionPeriod, ApiError, { period_start: string; period_end: string; cutoff_at: string; reason: string }>({
    mutationFn: (body) => requisitar('/commission-periods', { method: 'POST', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: key }),
  });
}

export function useCloseCommissionPeriod() {
  const client = useQueryClient();
  return useMutation<CommissionPeriod, ApiError, { id: number; reason: string }>({
    mutationFn: ({ id, reason }) => requisitar(`/commission-periods/${id}/closure`, { method: 'POST', body: { reason } }),
    onSuccess: () => void client.invalidateQueries({ queryKey: key }),
  });
}
