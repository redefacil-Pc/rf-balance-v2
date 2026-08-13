import { useQuery } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CollaboratorFunction } from '@/shared/types/organization';

/** Funções do colaborador: as vigentes primeiro, depois o histórico. */
export function useCollaboratorFunctions(collaboratorId: number | null) {
  return useQuery<CollaboratorFunction[], ApiError>({
    queryKey: collaboratorKeys.funcoes(collaboratorId ?? 0),
    queryFn: ({ signal }) =>
      requisitar<CollaboratorFunction[]>(`/collaborators/${collaboratorId}/functions`, {
        signal,
      }),
    enabled: collaboratorId !== null,
  });
}
