import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CommissionSettlement, CommissionSettlementPage } from '@/shared/types/commissions';

export interface Period {
  period_start: string;
  period_end: string;
}

const key = (period: Period) => ['commission-settlements', period] as const;

export function useSettlements(period: Period) {
  const enabled = Boolean(period.period_start && period.period_end);
  return useQuery<CommissionSettlementPage, ApiError>({
    queryKey: key(period),
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({
        period_start: period.period_start,
        period_end: period.period_end,
      });
      return requisitar<CommissionSettlementPage>(`/commission-settlements?${params}`, { signal });
    },
    enabled,
  });
}

export function useGenerateSettlements(period: Period) {
  const client = useQueryClient();
  return useMutation<CommissionSettlementPage, ApiError>({
    mutationFn: () => requisitar('/commission-settlements/generation', { method: 'POST', body: period }),
    onSuccess: (data) => client.setQueryData(key(period), data),
  });
}

export function useAdjustSettlement(period: Period) {
  const client = useQueryClient();
  return useMutation<CommissionSettlement, ApiError, { id: number; bonus_amount: string; discount_amount: string; deferred_amount: string; notes?: string }>({
    mutationFn: ({ id, ...body }) => requisitar(`/commission-settlements/${id}/adjustments`, { method: 'PUT', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: key(period) }),
  });
}

export function usePaySettlement(period: Period) {
  const client = useQueryClient();
  return useMutation<CommissionSettlement, ApiError, { id: number; amount: string; payment_date: string; payment_method: string; reference?: string }>({
    mutationFn: ({ id, ...body }) => requisitar(`/commission-settlements/${id}/payments`, { method: 'POST', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: key(period) }),
  });
}

export function useCreateBkoEntry() {
  return useMutation<unknown, ApiError, { beneficiary_id: number; amount: string; effective_date: string; description: string }>({
    mutationFn: (body) => requisitar('/commission-bko-entries', {
      method: 'POST', body, idempotencyKey: crypto.randomUUID(),
    }),
  });
}

export function useCreateFinalizationEntry() {
  return useMutation<unknown, ApiError, { beneficiary_id: number; amount: string; effective_date: string; description: string }>({
    mutationFn: (body) => requisitar('/commission-finalization-entries', {
      method: 'POST', body, idempotencyKey: crypto.randomUUID(),
    }),
  });
}
