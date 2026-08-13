import { useMutation, useQueryClient } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

/**
 * Encerra a sessão no servidor e limpa todo o cache — dado de um usuário nunca
 * pode sobrar visível para o próximo login na mesma aba.
 */
export function useLogout() {
  const client = useQueryClient();

  return useMutation<void, ApiError, void>({
    mutationFn: () => requisitar<void>('/auth/logout', { method: 'POST' }),
    onSettled: () => {
      client.clear();
    },
  });
}
