import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { LoginForm } from '@/features/auth/schemas/login-schema';
import { authKeys } from '@/features/auth/queries/auth-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { CurrentUser } from '@/shared/types/current-user';

/**
 * O backend responde com o usuário e grava os cookies. Nada de token é
 * manipulado aqui — o resultado só alimenta o cache de `/auth/me`.
 */
export function useLogin() {
  const client = useQueryClient();

  return useMutation<CurrentUser, ApiError, LoginForm>({
    mutationFn: (form) => requisitar<CurrentUser>('/auth/login', { method: 'POST', body: form }),
    onSuccess: (usuario) => {
      client.setQueryData(authKeys.me(), usuario);
    },
  });
}
