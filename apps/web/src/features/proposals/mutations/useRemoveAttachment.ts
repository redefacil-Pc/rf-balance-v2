import { useMutation, useQueryClient } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export interface RemocaoDeAnexo {
  proposalId: number;
  attachmentId: number;
}

/** Remove comprovante. Só vale enquanto a proposta é editável (rascunho/devolvida). */
export function useRemoveAttachment() {
  const client = useQueryClient();

  return useMutation<void, ApiError, RemocaoDeAnexo>({
    mutationFn: ({ proposalId, attachmentId }) =>
      requisitar<void>(`/proposals/${proposalId}/attachments/${attachmentId}`, {
        method: 'DELETE',
      }),
    onSuccess: (_resultado, { proposalId }) => {
      void client.invalidateQueries({ queryKey: proposalKeys.anexos(proposalId) });
    },
  });
}
