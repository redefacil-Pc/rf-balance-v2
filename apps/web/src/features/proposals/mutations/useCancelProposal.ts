import { useMutation, useQueryClient } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ProposalCancelResult } from '@/shared/types/commercial';

export interface CancelamentoDaProposta {
  id: number;
  version: number;
  reason: string;
}

/** Cancelamento é terminal e exige motivo: nada some do histórico. */
export function useCancelProposal() {
  const client = useQueryClient();

  return useMutation<ProposalCancelResult, ApiError, CancelamentoDaProposta>({
    mutationFn: ({ id, version, reason }) =>
      requisitar<ProposalCancelResult>(`/proposals/${id}/cancellation`, {
        method: 'POST',
        body: { version, reason },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: proposalKeys.todos });
    },
  });
}
