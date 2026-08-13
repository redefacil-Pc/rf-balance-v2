import { useQuery } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ProposalDetail } from '@/shared/types/commercial';

/** Detalhe da proposta. Só busca quando há uma proposta selecionada. */
export function useProposal(id: number | null) {
  return useQuery<ProposalDetail, ApiError>({
    queryKey: proposalKeys.detalhe(id ?? 0),
    queryFn: ({ signal }) => requisitar<ProposalDetail>(`/proposals/${id}`, { signal }),
    enabled: id !== null,
  });
}
