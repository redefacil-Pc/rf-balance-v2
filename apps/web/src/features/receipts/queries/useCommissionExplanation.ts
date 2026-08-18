import { useQuery } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CommissionExplanation } from '@/shared/types/receipts';

export function useCommissionExplanation(
  receiptId: number | null,
  proposalId: number | null = null,
) {
  const target = receiptId !== null
    ? `/receipts/${receiptId}/commission-calculations`
    : `/proposals/${proposalId}/commission-calculations`;
  return useQuery<CommissionExplanation, ApiError>({
    queryKey: ['commission-calculations', receiptId !== null ? 'receipt' : 'proposal', receiptId ?? proposalId],
    queryFn: ({ signal }) => requisitar<CommissionExplanation>(target, { signal }),
    enabled: receiptId !== null || proposalId !== null,
  });
}
