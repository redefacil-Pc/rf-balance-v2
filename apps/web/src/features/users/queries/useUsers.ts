import { useQuery } from '@tanstack/react-query';

import type { AccessRole, UserPage } from '@/features/users/types';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export const userKeys = { all: ['users'] as const, roles: ['users', 'roles'] as const };

export function useUsers() {
  return useQuery<UserPage, ApiError>({
    queryKey: userKeys.all,
    queryFn: ({ signal }) => requisitar<UserPage>('/users?limit=200', { signal }),
  });
}

export function useAccessRoles() {
  return useQuery<AccessRole[], ApiError>({
    queryKey: userKeys.roles,
    queryFn: ({ signal }) => requisitar<AccessRole[]>('/users/roles', { signal }),
    staleTime: 5 * 60 * 1000,
  });
}
