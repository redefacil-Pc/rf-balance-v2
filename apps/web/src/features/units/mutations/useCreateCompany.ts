import { useMutation, useQueryClient } from '@tanstack/react-query';

import { organizationKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { Company, Unit } from '@/shared/types/organization';

export interface CompanyInput {
  legal_name: string;
  trade_name: string;
  document?: string;
}

export function useCreateCompany() {
  const client = useQueryClient();

  return useMutation<Company, ApiError, CompanyInput>({
    mutationFn: (entrada) =>
      requisitar<Company>('/companies', {
        method: 'POST',
        body: { ...entrada, document: entrada.document || null },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: organizationKeys.empresas });
    },
  });
}

export interface UnitInput {
  company_id: number;
  code: string;
  name: string;
}

export function useCreateUnit() {
  const client = useQueryClient();

  return useMutation<Unit, ApiError, UnitInput>({
    mutationFn: (entrada) => requisitar<Unit>('/units', { method: 'POST', body: entrada }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['units'] });
    },
  });
}

export function useUpdateCompany() {
  const client = useQueryClient();
  return useMutation<void, ApiError, { id: number; legal_name: string; trade_name: string }>({
    mutationFn: ({ id, ...body }) => requisitar<void>(`/companies/${id}`, { method: 'PUT', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: organizationKeys.empresas }),
  });
}

export function useSetCompanyStatus() {
  const client = useQueryClient();
  return useMutation<void, ApiError, { id: number; is_active: boolean }>({
    mutationFn: ({ id, is_active }) => requisitar<void>(`/companies/${id}/status`, { method: 'PUT', body: { is_active } }),
    onSuccess: () => void client.invalidateQueries({ queryKey: organizationKeys.empresas }),
  });
}

export function useUpdateUnit() {
  const client = useQueryClient();
  return useMutation<void, ApiError, { id: number; code: string; name: string }>({
    mutationFn: ({ id, ...body }) => requisitar<void>(`/units/${id}`, { method: 'PUT', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['units'] }),
  });
}

export function useSetUnitStatus() {
  const client = useQueryClient();
  return useMutation<void, ApiError, { id: number; is_active: boolean }>({
    mutationFn: ({ id, is_active }) => requisitar<void>(`/units/${id}/status`, { method: 'PUT', body: { is_active } }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['units'] }),
  });
}
