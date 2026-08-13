import { useMutation, useQueryClient } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import type { ProposalForm } from '@/features/proposals/schemas/proposal-schema';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ProposalWriteResult } from '@/shared/types/commercial';

export function useCreateProposal() {
  const client = useQueryClient();

  return useMutation<ProposalWriteResult, ApiError, ProposalForm>({
    mutationFn: (form) =>
      requisitar<ProposalWriteResult>('/proposals', {
        method: 'POST',
        body: {
          consultant_id: form.consultant_id,
          business_date: form.business_date,
          customer_name: form.customer_name,
          customer_document: form.customer_document,
          // string decimal: a comissão quem calcula é o servidor
          operation_amount: form.operation_amount,
          tps_percentage: form.tps_percentage,
          external_id: form.external_id || null,
          bko_collaborator_id: form.bko_collaborator_id,
          finalizer_collaborator_id: form.finalizer_collaborator_id,
        },
      }),
    onSuccess: () => {
      // invalida por prefixo: qualquer combinação de filtro é refeita
      void client.invalidateQueries({ queryKey: proposalKeys.todos });
    },
  });
}
