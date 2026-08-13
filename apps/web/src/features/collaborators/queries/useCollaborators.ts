import { useInfiniteQuery } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CollaboratorPage } from '@/shared/types/organization';

export interface CollaboratorFilters {
  company_id?: number;
  unit_id?: number;
  role?: string;
  tax_regime?: string;
  only_active?: boolean;
  name?: string;
}

const TAMANHO_DA_PAGINA = 25;

function montarQuery(filtros: CollaboratorFilters, cursor?: string): string {
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
 * Paginação por cursor, não por página numerada: é o que o backend expõe e o
 * que mantém a listagem rápida conforme a base cresce.
 */
export function useCollaborators(filtros: CollaboratorFilters) {
  return useInfiniteQuery<CollaboratorPage, ApiError>({
    queryKey: collaboratorKeys.lista(filtros),
    queryFn: ({ pageParam, signal }) =>
      requisitar<CollaboratorPage>(
        `/collaborators?${montarQuery(filtros, pageParam as string | undefined)}`,
        { signal },
      ),
    initialPageParam: undefined,
    getNextPageParam: (ultima) => ultima.next_cursor ?? undefined,
  });
}
