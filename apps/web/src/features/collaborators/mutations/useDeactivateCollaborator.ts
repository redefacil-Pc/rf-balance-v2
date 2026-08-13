import { useMutation, useQueryClient } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

interface Entrada {
  id: number;
  deactivated_on: string;
  reason: string;
}

interface Resultado {
  id: number;
  closed_assignments: number;
}

/**
 * Inativação encerra os vínculos ativos do colaborador no servidor — a tela
 * precisa avisar quantos foram encerrados, porque isso afeta comissionamento.
 */
export function useDeactivateCollaborator() {
  const client = useQueryClient();

  return useMutation<Resultado, ApiError, Entrada>({
    mutationFn: ({ id, deactivated_on, reason }) =>
      requisitar<Resultado>(`/collaborators/${id}/deactivation`, {
        method: 'POST',
        body: { deactivated_on, reason },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: collaboratorKeys.todos });
    },
  });
}
