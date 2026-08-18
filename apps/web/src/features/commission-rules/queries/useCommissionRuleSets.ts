import { useQuery } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CommissionRuleSet } from '@/shared/types/commissions';

export const commissionRuleKeys = { all: ['commission-rule-sets'] as const };

export function useCommissionRuleSets() {
  return useQuery<CommissionRuleSet[], ApiError>({
    queryKey: commissionRuleKeys.all,
    queryFn: ({ signal }) => requisitar<CommissionRuleSet[]>('/commission-rule-sets', { signal }),
  });
}
