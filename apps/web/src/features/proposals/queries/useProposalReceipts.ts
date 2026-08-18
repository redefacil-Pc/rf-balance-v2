import { useQuery } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ReceiptPage } from '@/shared/types/receipts';

export function useProposalReceipts(proposalId: number | null) {
  return useQuery<ReceiptPage, ApiError>({
    queryKey: proposalId ? proposalKeys.recebimentos(proposalId) : [...proposalKeys.todos, 'receipts'],
    queryFn: () => requisitar(`/receipts?proposal_id=${proposalId}`),
    enabled: proposalId !== null,
  });
}
