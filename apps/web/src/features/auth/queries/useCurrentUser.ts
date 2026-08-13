import { useQuery } from '@tanstack/react-query';

import { authKeys } from '@/features/auth/queries/auth-keys';
import { requisitar } from '@/shared/api/http-client';
import { ApiError } from '@/shared/api/problem-details';
import type { CurrentUser } from '@/shared/types/current-user';

/**
 * Fonte única da identidade no cliente: derivada de `/auth/me`, nunca de leitura
 * de token. 401 não é retentado — significa "não autenticado", não falha.
 */
export function useCurrentUser() {
  return useQuery<CurrentUser, ApiError>({
    queryKey: authKeys.me(),
    queryFn: ({ signal }) => requisitar<CurrentUser>('/auth/me', { signal }),
    retry: (_tentativas, erro) => !(erro instanceof ApiError && erro.status === 401),
    staleTime: 5 * 60 * 1000,
  });
}
