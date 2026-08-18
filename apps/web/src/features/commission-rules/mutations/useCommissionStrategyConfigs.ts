import { useMutation, useQueryClient } from '@tanstack/react-query';

import { commissionStrategyConfigKeys } from '@/features/commission-rules/queries/useCommissionStrategyConfigs';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CommissionStrategyConfig, CommissionStrategyConfigInput } from '@/shared/types/commissions';

export function useCreateCommissionStrategyConfig() {
  const client = useQueryClient();
  return useMutation<CommissionStrategyConfig, ApiError, CommissionStrategyConfigInput>({
    mutationFn: (body) => requisitar('/commission-strategy-configs', { method: 'POST', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: commissionStrategyConfigKeys.all }),
  });
}

export function useActivateCommissionStrategyConfig() {
  const client = useQueryClient();
  return useMutation<CommissionStrategyConfig, ApiError, { id: number; reason: string }>({
    mutationFn: ({ id, reason }) => requisitar(`/commission-strategy-configs/${id}/activation`, { method: 'POST', body: { reason } }),
    onSuccess: () => void client.invalidateQueries({ queryKey: commissionStrategyConfigKeys.all }),
  });
}
