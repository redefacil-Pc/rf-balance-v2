import { useInfiniteQuery } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ProposalPage, StatusDaProposta } from '@/shared/types/commercial';

export interface ProposalFilters {
  status?: StatusDaProposta;
  consultant_id?: number;
  external_id?: string;
  customer_name?: string;
  business_date_from?: string;
  business_date_to?: string;
}

const TAMANHO_DA_PAGINA = 25;

function montarQuery(filtros: ProposalFilters, cursor?: string): string {
  const params = new URLSearchParams({ limit: String(TAMANHO_DA_PAGINA) });
  for (const [chave, valor] of Object.entries(filtros)) {
    if (valor !== undefined && valor !== '') {
      params.set(chave, String(valor));
    }
  }
  if (cursor) {
    params.set('cursor', cursor);
  }
  return params.toString();
}

/**
 * Paginação por cursor: a listagem de propostas é a tela que mais cresce, e
 * `OFFSET` alto é a causa clássica de lentidão conforme a base aumenta.
 */
export function useProposals(filtros: ProposalFilters) {
  return useInfiniteQuery<ProposalPage, ApiError>({
    queryKey: proposalKeys.lista(filtros),
    queryFn: ({ pageParam, signal }) =>
      requisitar<ProposalPage>(
        `/proposals?${montarQuery(filtros, pageParam as string | undefined)}`,
        { signal },
      ),
    initialPageParam: undefined,
    getNextPageParam: (ultima) => ultima.next_cursor ?? undefined,
  });
}
