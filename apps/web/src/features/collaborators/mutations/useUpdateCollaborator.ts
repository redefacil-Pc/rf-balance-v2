import { useMutation, useQueryClient } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { TaxRegime } from '@/shared/types/organization';

interface Entrada { id: number; company_id: number; unit_id: number | null; full_name: string; tax_regime: TaxRegime; email: string | null; phone: string | null; payment_key?: { key_type: string; key: string }; consultant_modality?: 'CONSULTOR' | 'CONSULTOR_MEI_ESCALONADO'; modality_valid_from?: string; modality_reason?: string }

export function useUpdateCollaborator() {
  const client = useQueryClient();
  return useMutation<void, ApiError, Entrada>({
    mutationFn: ({ id, ...body }) => requisitar<void>(`/collaborators/${id}`, { method: 'PUT', body }),
    onSuccess: (_data, input) => {
      void client.invalidateQueries({ queryKey: collaboratorKeys.todos });
      void client.invalidateQueries({ queryKey: collaboratorKeys.funcoes(input.id) });
    },
  });
}
