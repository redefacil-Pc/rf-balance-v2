import { useQuery } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ProposalAttachment } from '@/shared/types/commercial';

/** Comprovantes de pagamento da proposta, na ordem de envio. */
export function useProposalAttachments(proposalId: number | null) {
  return useQuery<ProposalAttachment[], ApiError>({
    queryKey: proposalKeys.anexos(proposalId ?? 0),
    queryFn: ({ signal }) =>
      requisitar<ProposalAttachment[]>(`/proposals/${proposalId}/attachments`, { signal }),
    enabled: proposalId !== null,
  });
}
