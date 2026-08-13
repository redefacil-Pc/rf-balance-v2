import { useQuery } from '@tanstack/react-query';

import { organizationKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { Company, Unit } from '@/shared/types/organization';

export function useCompanies(onlyActive = true) {
  return useQuery<Company[], ApiError>({
    queryKey: [...organizationKeys.empresas, onlyActive],
    queryFn: ({ signal }) => requisitar<Company[]>(`/companies?only_active=${onlyActive}`, { signal }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useUnits(companyId?: number, onlyActive = true) {
  return useQuery<Unit[], ApiError>({
    queryKey: [...organizationKeys.unidades(companyId), onlyActive],
    queryFn: ({ signal }) =>
      requisitar<Unit[]>(`/units?only_active=${onlyActive}${companyId ? `&company_id=${companyId}` : ''}`, { signal }),
    staleTime: 5 * 60 * 1000,
  });
}
