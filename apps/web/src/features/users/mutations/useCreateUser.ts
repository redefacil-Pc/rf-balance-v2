import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { UserForm } from '@/features/users/schemas/user-schema';
import { userKeys } from '@/features/users/queries/useUsers';
import type { CreatedUser } from '@/features/users/types';
import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export function useCreateUser() {
  const client = useQueryClient();
  return useMutation<CreatedUser, ApiError, UserForm>({
    mutationFn: (form) =>
      requisitar<CreatedUser>('/users', {
        method: 'POST',
        body: {
          email: form.email,
          full_name: form.full_name,
          roles: form.roles,
          // nulo quando a pessoa só usa o sistema: administração e financeiro
          // não são necessariamente colaboradores comissionados
          collaborator: form.is_collaborator
            ? {
                company_id: form.company_id,
                unit_id: form.unit_id,
                document: form.document,
                tax_regime: form.tax_regime,
                function: form.function,
                valid_from: form.valid_from,
              }
            : null,
        },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: userKeys.all });
      void client.invalidateQueries({ queryKey: collaboratorKeys.todos });
    },
  });
}
