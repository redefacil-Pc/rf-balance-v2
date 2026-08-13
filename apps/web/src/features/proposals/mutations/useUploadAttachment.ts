import { useMutation, useQueryClient } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export interface AnexoDaProposta {
  proposalId: number;
  file: File;
}

interface AttachmentUploadResult {
  id: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
}

/** Anexa o comprovante de pagamento. Só vale enquanto a proposta é editável. */
export function useUploadAttachment() {
  const client = useQueryClient();

  return useMutation<AttachmentUploadResult, ApiError, AnexoDaProposta>({
    mutationFn: ({ proposalId, file }) => {
      const corpo = new FormData();
      corpo.append('file', file);
      return requisitar<AttachmentUploadResult>(`/proposals/${proposalId}/attachments`, {
        method: 'POST',
        body: corpo,
      });
    },
    onSuccess: (_resultado, { proposalId }) => {
      void client.invalidateQueries({ queryKey: proposalKeys.anexos(proposalId) });
    },
  });
}
