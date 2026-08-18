import { useQuery } from '@tanstack/react-query';

import type { AccessRole, UserPage } from '@/features/users/types';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export const userKeys = { all: ['users'] as const, roles: ['users', 'roles'] as const };

export interface UserFilters { search?: string; role?: string; is_active?: boolean }

export function useUsers(filters: UserFilters = {}) {
  const params = new URLSearchParams({ limit: '200' });
  if (filters.search) params.set('search', filters.search);
  if (filters.role) params.set('role', filters.role);
  if (filters.is_active !== undefined) params.set('is_active', String(filters.is_active));
  return useQuery<UserPage, ApiError>({
    queryKey: [...userKeys.all, filters],
    queryFn: async ({ signal }) => {
      const items: UserPage['items'] = [];
      let cursor: string | null = null;
      do {
        const pageParams = new URLSearchParams(params);
        if (cursor) pageParams.set('cursor', cursor);
        const page = await requisitar<UserPage>(`/users?${pageParams}`, { signal });
        items.push(...page.items);
        cursor = page.next_cursor;
      } while (cursor);
      return { items, next_cursor: null };
    },
  });
}

export function useAccessRoles() {
  return useQuery<AccessRole[], ApiError>({
    queryKey: userKeys.roles,
    queryFn: ({ signal }) => requisitar<AccessRole[]>('/users/roles', { signal }),
    staleTime: 5 * 60 * 1000,
  });
}
