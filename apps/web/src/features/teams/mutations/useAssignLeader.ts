import { useMutation, useQueryClient } from '@tanstack/react-query';

import { teamKeys } from '@/features/teams/queries/useAssignments';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { Assignment } from '@/shared/types/organization';

export interface AssignLeaderInput {
  consultant_id: number;
  leader_id: number;
  assignment_type: string;
  start_date: string;
  reason: string;
}

/**
 * Se já existe vínculo vigente, o backend o encerra no dia anterior e devolve
 * `previous_closed_on` — a tela precisa mostrar isso, porque muda a atribuição
 * de comissão do período.
 */
export function useAssignLeader() {
  const client = useQueryClient();

  return useMutation<Assignment, ApiError, AssignLeaderInput>({
    mutationFn: (entrada) =>
      requisitar<Assignment>('/assignments', { method: 'POST', body: entrada }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: teamKeys.todos });
    },
  });
}
