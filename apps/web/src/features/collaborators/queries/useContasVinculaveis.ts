import { useQuery } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

/** O mínimo que a tela precisa de uma conta para oferecê-la no vínculo. */
export interface ContaVinculavel {
  id: number;
  email: string;
  full_name: string;
  roles: string[];
  is_active: boolean;
}

interface Pagina {
  items: ContaVinculavel[];
  next_cursor?: string | null;
}

/**
 * Contas ainda sem cadastro operacional — as candidatas ao vínculo.
 *
 * Vive aqui, e não em `features/users`, porque quem consome é o cadastro de
 * colaborador: import cruzado entre features é proibido, e o endpoint é
 * terreno comum.
 */
export function useContasVinculaveis(habilitado = true) {
  return useQuery<Pagina, ApiError>({
    queryKey: collaboratorKeys.contasVinculaveis,
    queryFn: async ({ signal }) => {
      const items: ContaVinculavel[] = [];
      let cursor: string | null = null;
      do {
        const params = new URLSearchParams({
          has_collaborator: 'false',
          is_active: 'true',
          limit: '200',
        });
        if (cursor) params.set('cursor', cursor);
        const page = await requisitar<Pagina>(`/users?${params}`, { signal });
        items.push(...page.items);
        cursor = page.next_cursor ?? null;
      } while (cursor);
      return { items, next_cursor: null };
    },
    enabled: habilitado,
  });
}
