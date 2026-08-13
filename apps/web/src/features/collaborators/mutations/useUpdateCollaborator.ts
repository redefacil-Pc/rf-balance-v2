import { useMutation, useQueryClient } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { TaxRegime } from '@/shared/types/organization';

interface Entrada { id: number; company_id: number; unit_id: number | null; full_name: string; tax_regime: TaxRegime; email: string | null; phone: string | null; payment_key?: { key_type: string; key: string } }

export function useUpdateCollaborator() {
  const client = useQueryClient();
  return useMutation<void, ApiError, Entrada>({
    mutationFn: ({ id, ...body }) => requisitar<void>(`/collaborators/${id}`, { method: 'PUT', body }),
    onSuccess: () => void client.invalidateQueries({ queryKey: collaboratorKeys.todos }),
  });
}
