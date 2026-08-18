import { useQuery } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ActiveTeamAssignment, Assignment } from '@/shared/types/organization';

export const teamKeys = {
  todos: ['assignments'] as const,
  doConsultor: (consultantId: number) => [...teamKeys.todos, 'consultant', consultantId] as const,
  liderNaData: (consultantId: number, data: string, tipo: string) =>
    [...teamKeys.todos, 'leader', consultantId, data, tipo] as const,
  vigentes: (data: string) => [...teamKeys.todos, 'active', data] as const,
};

export function useActiveAssignments(referenceDate: string) {
  return useQuery<ActiveTeamAssignment[], ApiError>({
    queryKey: teamKeys.vigentes(referenceDate),
    queryFn: ({ signal }) =>
      requisitar<ActiveTeamAssignment[]>(
        `/assignments/active?reference_date=${referenceDate}`,
        { signal },
      ),
    enabled: Boolean(referenceDate),
  });
}

export function useAssignmentHistory(consultantId: number | undefined) {
  return useQuery<Assignment[], ApiError>({
    queryKey: teamKeys.doConsultor(consultantId ?? 0),
    queryFn: ({ signal }) =>
      requisitar<Assignment[]>(`/assignments/consultant/${consultantId}`, { signal }),
    enabled: Boolean(consultantId),
  });
}

/** A mesma consulta que o motor de comissão usará na F4. */
export function useLeaderAtDate(
  consultantId: number | undefined,
  referenceDate: string,
  assignmentType: string,
) {
  return useQuery<Assignment | null, ApiError>({
    queryKey: teamKeys.liderNaData(consultantId ?? 0, referenceDate, assignmentType),
    queryFn: ({ signal }) =>
      requisitar<Assignment | null>(
        `/assignments/leader?consultant_id=${consultantId}` +
          `&reference_date=${referenceDate}&assignment_type=${assignmentType}`,
        { signal },
      ),
    enabled: Boolean(consultantId && referenceDate),
  });
}
