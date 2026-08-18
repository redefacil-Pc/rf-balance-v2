import { useMutation, useQueryClient } from '@tanstack/react-query';
import { teamKeys } from '@/features/teams/queries/useAssignments';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export function useCloseAssignment(consultantId?: number) {
  const client = useQueryClient();
  return useMutation<void, ApiError, { id: number; end_date: string; reason: string }>({
    mutationFn: ({ id, ...body }) =>
      requisitar<void>(`/assignments/${id}/closure`, { method: 'PUT', body }),
    onSuccess: () => {
      if (consultantId) {
        void client.invalidateQueries({ queryKey: teamKeys.doConsultor(consultantId) });
      }
      void client.invalidateQueries({ queryKey: teamKeys.todos });
    },
  });
}
