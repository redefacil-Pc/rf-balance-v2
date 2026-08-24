import { useQuery } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

interface PendingProposalCount {
  count: number;
}

export function usePendingProposalCount(enabled: boolean) {
  return useQuery<PendingProposalCount, ApiError>({
    queryKey: [...proposalKeys.todos, 'pending-count'],
    queryFn: ({ signal }) => requisitar<PendingProposalCount>('/proposals/pending-count', { signal }),
    enabled,
    refetchInterval: 30_000,
  });
}
