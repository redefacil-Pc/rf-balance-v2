import { useMutation, useQueryClient } from '@tanstack/react-query';

import { commissionRuleKeys } from '@/features/commission-rules/queries/useCommissionRuleSets';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CommissionRuleSet, CommissionRuleSetInput } from '@/shared/types/commissions';

export function useCreateCommissionRuleSet() {
  const client = useQueryClient();
  return useMutation<CommissionRuleSet, ApiError, CommissionRuleSetInput>({
    mutationFn: (body) =>
      requisitar<CommissionRuleSet>('/commission-rule-sets', { method: 'POST', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: commissionRuleKeys.all }),
  });
}

export function useActivateCommissionRuleSet() {
  const client = useQueryClient();
  return useMutation<CommissionRuleSet, ApiError, { id: number; reason: string }>({
    mutationFn: ({ id, reason }) =>
      requisitar<CommissionRuleSet>(`/commission-rule-sets/${id}/activation`, {
        method: 'POST',
        body: { reason },
      }),
    onSuccess: () => void client.invalidateQueries({ queryKey: commissionRuleKeys.all }),
  });
}
