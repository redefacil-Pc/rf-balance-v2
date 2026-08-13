import { useMutation, useQueryClient } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { SubmitProposalResult } from '@/shared/types/commercial';

export interface EnvioDaProposta {
  id: number;
  version: number;
}

/** Envia a proposta ao financeiro. Sem comprovante o backend recusa. */
export function useSubmitProposal() {
  const client = useQueryClient();

  return useMutation<SubmitProposalResult, ApiError, EnvioDaProposta>({
    mutationFn: ({ id, version }) =>
      requisitar<SubmitProposalResult>(`/proposals/${id}/submission`, {
        method: 'POST',
        body: { version },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: proposalKeys.todos });
    },
  });
}
