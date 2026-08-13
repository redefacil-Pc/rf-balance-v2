import { useQuery } from '@tanstack/react-query';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CollaboratorDetail } from '@/shared/types/organization';

export function useCollaboratorDetail(id: number | null) {
  return useQuery<CollaboratorDetail, ApiError>({
    queryKey: ['collaborators', id, 'details'],
    queryFn: ({ signal }) => requisitar<CollaboratorDetail>(`/collaborators/${id}/details`, { signal }),
    enabled: id !== null,
  });
}
