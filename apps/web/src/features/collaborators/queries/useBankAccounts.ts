import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export interface BankAccount { id: number; bank_code: string; bank_name: string; branch: string; account_masked: string; account_type: string; is_active: boolean }
export interface BankAccountInput { bank_code: string; bank_name: string; branch: string; account_number?: string | null; account_type: string }
const key = (id: number | null) => ['collaborators', id, 'bank-accounts'] as const;

export function useBankAccounts(id: number | null) { return useQuery<BankAccount[], ApiError>({ queryKey: key(id), queryFn: ({ signal }) => requisitar<BankAccount[]>(`/collaborators/${id}/bank-accounts`, { signal }), enabled: id !== null }); }
export function useSaveBankAccount(collaboratorId: number) { const client = useQueryClient(); return useMutation<unknown, ApiError, BankAccountInput & { id?: number }>({ mutationFn: ({ id, ...body }) => requisitar(id ? `/collaborators/${collaboratorId}/bank-accounts/${id}` : `/collaborators/${collaboratorId}/bank-accounts`, { method: id ? 'PUT' : 'POST', body }), onSuccess: () => void client.invalidateQueries({ queryKey: key(collaboratorId) }) }); }
export function useSetBankAccountStatus(collaboratorId: number) { const client = useQueryClient(); return useMutation<void, ApiError, { id: number; is_active: boolean }>({ mutationFn: ({ id, is_active }) => requisitar<void>(`/collaborators/${collaboratorId}/bank-accounts/${id}/status`, { method: 'PUT', body: { is_active } }), onSuccess: () => void client.invalidateQueries({ queryKey: key(collaboratorId) }) }); }
