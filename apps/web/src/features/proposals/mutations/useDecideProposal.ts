import { useMutation, useQueryClient } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { DecisionResult } from '@/shared/types/commercial';

export interface DecisaoDaProposta {
  id: number;
  version: number;
  decision: 'APROVAR' | 'DEVOLVER';
  /** Obrigatório quando `decision` é DEVOLVER. */
  reason?: string;
}

/** Decisão do financeiro: aprova ou devolve com motivo. */
export function useDecideProposal() {
  const client = useQueryClient();

  return useMutation<DecisionResult, ApiError, DecisaoDaProposta>({
    mutationFn: ({ id, version, decision, reason }) =>
      requisitar<DecisionResult>(`/proposals/${id}/decision`, {
        method: 'POST',
        body: { version, decision, reason: reason ?? null },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: proposalKeys.todos });
    },
  });
}
