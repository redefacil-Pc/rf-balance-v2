import { z } from 'zod';

import { apenasDigitos, temTamanhoDeDocumento } from '@/shared/formatters/document-mask';
import { PAPEIS } from '@/shared/types/organization';

/**
 * Validação de forma no cliente. O dígito verificador do documento e a
 * sobreposição de vigências são validados no backend — aqui só evitamos o
 * ida-e-volta óbvio.
 *
 * O documento chega mascarado, como o operador o vê, e sai em dígitos — a
 * conversão é feita no `transform`. A chave PIX é normalizada na mutation, junto
 * da montagem do payload, porque depende do tipo escolhido.
 */
export const collaboratorSchema = z
  .object({
    company_id: z.number({ required_error: 'Selecione a empresa' }).int().positive(),
    unit_id: z.number().int().positive().nullable(),
    full_name: z
      .string()
      .min(3, 'Informe o nome completo')
      .max(200)
      .transform((valor) => valor.trim()),
    document: z
      .string()
      .min(1, 'Informe o CPF ou CNPJ')
      .refine(temTamanhoDeDocumento, 'O documento deve ter 11 dígitos (CPF) ou 14 (CNPJ)')
      .transform(apenasDigitos),
    tax_regime: z.enum(['MEI', 'CLT'], { required_error: 'Selecione o regime' }),
    roles: z
      .array(
        z.object({
          role: z.enum(PAPEIS),
          valid_from: z.string().min(1, 'Informe o início da vigência'),
        }),
      )
      .min(1, 'Informe ao menos uma função'),
    email: z.string().email('E-mail inválido').or(z.literal('')).optional(),
    /**
     * Conta de acesso existente, vinculada no mesmo commit. Nulo para quem não
     * usa o sistema — o BKO, por exemplo, é só cadastro.
     */
    user_id: z.number().int().positive().nullable().optional(),
    payment_key_type: z.enum(['CPF', 'CNPJ', 'EMAIL', 'TELEFONE', 'ALEATORIA']).optional(),
    payment_key: z.string().max(140).optional(),
  })
  .refine((dados) => !dados.payment_key || Boolean(dados.payment_key_type), {
    message: 'Informe o tipo da chave PIX',
    path: ['payment_key_type'],
  })
  .refine(
    (dados) => dados.roles.filter(({ role }) => role === 'CONSULTOR' || role === 'CONSULTOR_MEI_ESCALONADO').length <= 1,
    {
      message: 'Escolha apenas uma modalidade de consultor: padrão ou escalonado',
      path: ['roles'],
    },
  );

export type CollaboratorForm = z.infer<typeof collaboratorSchema>;

/** O que o formulário guarda — mascarado — antes do `transform`. */
export type CollaboratorFormEntrada = z.input<typeof collaboratorSchema>;
