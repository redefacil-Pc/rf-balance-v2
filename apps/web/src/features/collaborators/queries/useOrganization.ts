import { useQuery } from '@tanstack/react-query';

import { organizationKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { Company, Unit } from '@/shared/types/organization';

export function useCompanies() {
  return useQuery<Company[], ApiError>({
    queryKey: organizationKeys.empresas,
    queryFn: ({ signal }) => requisitar<Company[]>('/companies', { signal }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useUnits(companyId?: number) {
  return useQuery<Unit[], ApiError>({
    queryKey: organizationKeys.unidades(companyId),
    queryFn: ({ signal }) =>
      requisitar<Unit[]>(companyId ? `/units?company_id=${companyId}` : '/units', { signal }),
    staleTime: 5 * 60 * 1000,
  });
}
