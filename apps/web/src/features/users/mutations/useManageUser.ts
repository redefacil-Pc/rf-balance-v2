import { useMutation, useQueryClient } from '@tanstack/react-query';

import { userKeys } from '@/features/users/queries/useUsers';
import type { SystemUser } from '@/features/users/types';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export function useUpdateUser() {
  const client = useQueryClient();
  return useMutation<SystemUser, ApiError, { id: number; full_name: string; email: string; roles?: string[]; is_active?: boolean }>({
    mutationFn: ({ id, ...body }) => requisitar<SystemUser>(`/users/${id}`, { method: 'PUT', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: userKeys.all }),
  });
}

export function useSetUserRoles() {
  const client = useQueryClient();
  return useMutation<SystemUser, ApiError, { id: number; roles: string[] }>({
    mutationFn: ({ id, roles }) => requisitar<SystemUser>(`/users/${id}/roles`, { method: 'PUT', body: { roles } }),
    onSuccess: () => void client.invalidateQueries({ queryKey: userKeys.all }),
  });
}

export function useSetUserStatus() {
  const client = useQueryClient();
  return useMutation<SystemUser, ApiError, { id: number; is_active: boolean }>({
    mutationFn: ({ id, is_active }) => requisitar<SystemUser>(`/users/${id}/status`, { method: 'PUT', body: { is_active } }),
    onSuccess: () => void client.invalidateQueries({ queryKey: userKeys.all }),
  });
}

export interface PasswordResetResult {
  id: number;
  email: string;
  /** Só vem preenchida quando o sistema gerou; nula quando a senha foi definida. */
  temporary_password: string | null;
  must_change_password: boolean;
}

export interface PasswordReset {
  id: number;
  /** Ausente gera uma provisória; presente define a senha informada. */
  password?: string;
  require_change?: boolean;
}

export function useResetUserPassword() {
  const client = useQueryClient();
  return useMutation<PasswordResetResult, ApiError, PasswordReset>({
    mutationFn: ({ id, password, require_change = true }) =>
      requisitar<PasswordResetResult>(`/users/${id}/password-reset`, {
        method: 'POST',
        body: { password: password ?? null, require_change },
      }),
    // `must_change_password` muda na listagem
    onSuccess: () => void client.invalidateQueries({ queryKey: userKeys.all }),
  });
}
