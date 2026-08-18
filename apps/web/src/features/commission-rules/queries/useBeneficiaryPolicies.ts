import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CommissionBeneficiaryPolicy } from '@/shared/types/commissions';

const key = ['commission-beneficiary-policies'] as const;

export function useBeneficiaryPolicies() {
  return useQuery<CommissionBeneficiaryPolicy[], ApiError>({
    queryKey: key,
    queryFn: ({ signal }) => requisitar('/commission-beneficiary-policies', { signal }),
  });
}

export function useCreateBeneficiaryPolicy() {
  const client = useQueryClient();
  return useMutation<CommissionBeneficiaryPolicy, ApiError, {
    collaborator_id: number;
    valid_from: string;
    excluded: boolean;
    override_tps_35_percentage: string | null;
    reason: string;
  }>({
    mutationFn: (body) => requisitar('/commission-beneficiary-policies', { method: 'POST', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: key }),
  });
}
