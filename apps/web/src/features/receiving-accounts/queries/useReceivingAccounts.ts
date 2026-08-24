import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ReceivingAccount } from '@/shared/types/receiving-accounts';

const key = (apenasAtivas: boolean) => ['receiving-accounts', { apenasAtivas }] as const;

export function useReceivingAccounts(apenasAtivas = false, habilitada = true) {
  return useQuery<ReceivingAccount[], ApiError>({
    queryKey: key(apenasAtivas),
    queryFn: ({ signal }) =>
      requisitar(`/receiving-accounts${apenasAtivas ? '?only_active=true' : ''}`, { signal }),
    enabled: habilitada,
  });
}

interface Entrada {
  id?: number;
  label: string;
  display_order?: number | null;
}

export function useSaveReceivingAccount() {
  const client = useQueryClient();
  return useMutation<ReceivingAccount, ApiError, Entrada>({
    mutationFn: ({ id, ...body }) =>
      requisitar(id ? `/receiving-accounts/${id}` : '/receiving-accounts', {
        method: id ? 'PUT' : 'POST',
        body,
      }),
    // invalida por prefixo: a lista completa e a de ativas mudam juntas
    onSuccess: () => void client.invalidateQueries({ queryKey: ['receiving-accounts'] }),
  });
}

export function useSetReceivingAccountStatus() {
  const client = useQueryClient();
  return useMutation<ReceivingAccount, ApiError, { id: number; is_active: boolean }>({
    mutationFn: ({ id, is_active }) =>
      requisitar(`/receiving-accounts/${id}/status`, { method: 'PUT', body: { is_active } }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['receiving-accounts'] }),
  });
}
