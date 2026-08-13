import { useMutation, useQueryClient } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import type { UpdateProposalForm } from '@/features/proposals/schemas/proposal-schema';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ProposalWriteResult } from '@/shared/types/commercial';

export interface AlteracaoDaProposta {
  id: number;
  /** Versão que esta tela leu; divergiu no servidor, a alteração é recusada. */
  version: number;
  form: UpdateProposalForm;
}

export function useUpdateProposal() {
  const client = useQueryClient();

  return useMutation<ProposalWriteResult, ApiError, AlteracaoDaProposta>({
    mutationFn: ({ id, version, form }) =>
      requisitar<ProposalWriteResult>(`/proposals/${id}`, {
        method: 'PUT',
        body: {
          version,
          operation_amount: form.operation_amount,
          tps_percentage: form.tps_percentage,
          bko_collaborator_id: form.bko_collaborator_id,
          finalizer_collaborator_id: form.finalizer_collaborator_id,
        },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: proposalKeys.todos });
    },
  });
}
