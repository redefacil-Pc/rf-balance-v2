import { useMutation, useQueryClient } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CollaboratorFunction, Papel } from '@/shared/types/organization';

export interface AberturaDeFuncao {
  collaboratorId: number;
  function: Papel;
  valid_from: string;
}

export interface EncerramentoDeFuncao {
  collaboratorId: number;
  functionId: number;
  valid_to: string;
}

/** Abre função. Acumular funções diferentes é o modelo, não exceção. */
export function useAddFunction() {
  const client = useQueryClient();

  return useMutation<CollaboratorFunction, ApiError, AberturaDeFuncao>({
    mutationFn: ({ collaboratorId, ...corpo }) =>
      requisitar<CollaboratorFunction>(`/collaborators/${collaboratorId}/functions`, {
        method: 'POST',
        body: corpo,
      }),
    onSuccess: (_resultado, { collaboratorId }) => {
      void client.invalidateQueries({ queryKey: collaboratorKeys.funcoes(collaboratorId) });
      // a listagem mostra a função vigente na coluna de papéis
      void client.invalidateQueries({ queryKey: collaboratorKeys.todos });
    },
  });
}

/**
 * Encerra a vigência. A linha permanece: é ela que responde qual era a função
 * na data de uma proposta antiga.
 */
export function useCloseFunction() {
  const client = useQueryClient();

  return useMutation<CollaboratorFunction, ApiError, EncerramentoDeFuncao>({
    mutationFn: ({ collaboratorId, functionId, valid_to }) =>
      requisitar<CollaboratorFunction>(
        `/collaborators/${collaboratorId}/functions/${functionId}/closure`,
        { method: 'PUT', body: { valid_to } },
      ),
    onSuccess: (_resultado, { collaboratorId }) => {
      void client.invalidateQueries({ queryKey: collaboratorKeys.funcoes(collaboratorId) });
      void client.invalidateQueries({ queryKey: collaboratorKeys.todos });
    },
  });
}
