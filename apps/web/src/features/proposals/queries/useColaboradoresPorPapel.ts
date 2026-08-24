import { useQuery } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CollaboratorPage } from '@/shared/types/organization';

/**
 * Colaboradores ativos de um papel, para os selects da proposta.
 *
 * Uma proposta cita consultor, BKO e finalizador; cada select carrega só o papel
 * que lhe interessa, com a vigência resolvida pelo backend na data de hoje.
 */
export function useColaboradoresPorPapel(papel: string | readonly string[]) {
  const papeis = typeof papel === 'string' ? [papel] : [...papel];
  return useQuery<CollaboratorPage, ApiError>({
    queryKey: ['collaborators', 'options', ...papeis],
    queryFn: async ({ signal }) => {
      const paginas = await Promise.all(
        papeis.map((funcao) =>
          requisitar<CollaboratorPage>(
            `/collaborators?role=${funcao}&only_active=true&limit=200`,
            { signal },
          ),
        ),
      );
      const unicos = new Map(
        paginas.flatMap((pagina) => pagina.items).map((colaborador) => [colaborador.id, colaborador]),
      );
      return { items: [...unicos.values()], next_cursor: null };
    },
    staleTime: 5 * 60 * 1000,
  });
}
