import { useMutation, useQueryClient } from '@tanstack/react-query';

import { collaboratorKeys } from '@/features/collaborators/queries/collaborator-keys';
import type { CollaboratorForm } from '@/features/collaborators/schemas/collaborator-schema';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import { apenasDigitos } from '@/shared/formatters/document-mask';
import type { TipoDeChavePix } from '@/shared/formatters/pix-mask';
import type { Collaborator } from '@/shared/types/organization';

const CHAVES_NUMERICAS: TipoDeChavePix[] = ['CPF', 'CNPJ', 'TELEFONE'];

function chaveSemMascara(tipo: TipoDeChavePix, chave: string): string {
  return CHAVES_NUMERICAS.includes(tipo) ? apenasDigitos(chave) : chave;
}

export function useCreateCollaborator() {
  const client = useQueryClient();

  return useMutation<Collaborator, ApiError, CollaboratorForm>({
    mutationFn: (form) =>
      requisitar<Collaborator>('/collaborators', {
        method: 'POST',
        body: {
          company_id: form.company_id,
          unit_id: form.unit_id,
          full_name: form.full_name,
          document: form.document,
          tax_regime: form.tax_regime,
          roles: form.roles,
          user_id: form.user_id ?? null,
          email: form.email || null,
          // `phone` existe no contrato da API, mas a tela não coleta telefone —
          // o contato do colaborador é o e-mail e a chave PIX
          phone: null,
          payment_key:
            form.payment_key && form.payment_key_type
              ? {
                  key_type: form.payment_key_type,
                  // chave numérica vai em dígitos; e-mail e chave aleatória vão
                  // como digitados — mascarar esses dois corromperia a chave
                  key: chaveSemMascara(form.payment_key_type, form.payment_key),
                }
              : null,
        },
      }),
    onSuccess: () => {
      // invalida por prefixo: qualquer combinação de filtro é refeita
      void client.invalidateQueries({ queryKey: collaboratorKeys.todos });
      // a conta vinculada sai da lista de vinculáveis e ganha colaborador.
      // Chave literal, não importada de `features/users`: import cruzado entre
      // features é proibido.
      void client.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
