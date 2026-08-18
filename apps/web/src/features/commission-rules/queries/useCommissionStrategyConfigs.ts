import { useQuery } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CommissionStrategyConfig } from '@/shared/types/commissions';

export const commissionStrategyConfigKeys = { all: ['commission-strategy-configs'] as const };

export function useCommissionStrategyConfigs() {
  return useQuery<CommissionStrategyConfig[], ApiError>({
    queryKey: commissionStrategyConfigKeys.all,
    queryFn: ({ signal }) => requisitar<CommissionStrategyConfig[]>('/commission-strategy-configs', { signal }),
  });
}
