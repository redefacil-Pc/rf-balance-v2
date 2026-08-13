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
}

interface Pagina {
  items: ContaVinculavel[];
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
    queryFn: ({ signal }) =>
      requisitar<Pagina>('/users?has_collaborator=false&limit=200', { signal }),
    enabled: habilitado,
  });
}
