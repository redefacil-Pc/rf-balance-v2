import { useMutation, useQueryClient } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export function useLinkCollaboratorAccount() {
  const client = useQueryClient();
  return useMutation<void, ApiError, { collaboratorId: number; userId: number | null }>({
    mutationFn: ({ collaboratorId, userId }) =>
      requisitar<void>(`/collaborators/${collaboratorId}/account`, {
        method: 'PUT',
        body: { user_id: userId },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: collaboratorKeys.todos });
      void client.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
