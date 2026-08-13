import { z } from 'zod';

import { apenasDigitos, temTamanhoDeDocumento } from '@/shared/formatters/document-mask';
import { PAPEIS } from '@/shared/types/organization';

export const ACCESS_ROLES = [
  'ADMIN',
  'FINANCEIRO',
  'OPERACIONAL',
  'LIDERANCA',
  'CONSULTOR',
] as const;

/**
 * Conta de acesso e cadastro operacional são eixos independentes.
 *
 * Quem administra ou trabalha no financeiro costuma não ser colaborador
 * comissionado: exigir CPF, empresa e uma função operacional dessa pessoa
 * obrigaria a inventar dado que não existe — e dado inventado suja o cálculo de
 * comissão depois. Por isso o bloco operacional é opcional, e os campos dele só
 * são cobrados quando `is_collaborator` está ligado.
 */
const camposOperacionais = {
  company_id: z.number().int().positive().nullable(),
  unit_id: z.number().int().positive().nullable(),
  document: z.string(),
  tax_regime: z.enum(['MEI', 'CLT']),
  function: z.enum(PAPEIS),
  valid_from: z.string(),
};

export const userSchema = z
  .object({
    full_name: z.string().min(3, 'Informe o nome completo').max(200).transform((v) => v.trim()),
    email: z.string().email('E-mail inválido').max(320),
    roles: z.array(z.enum(ACCESS_ROLES)).min(1, 'Selecione ao menos um perfil de acesso'),
    is_collaborator: z.boolean(),
    ...camposOperacionais,
  })
  .superRefine((valor, ctx) => {
    if (!valor.is_collaborator) {
      return;
    }
    const exigir = (campo: keyof typeof camposOperacionais, mensagem: string) =>
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: [campo], message: mensagem });

    if (!valor.company_id) {
      exigir('company_id', 'Selecione a empresa');
    }
    if (!temTamanhoDeDocumento(valor.document)) {
      exigir('document', 'O documento deve ter 11 ou 14 dígitos');
    }
    if (!valor.valid_from) {
      exigir('valid_from', 'Informe o início da vigência');
    }
  })
  // a máscara some só aqui, depois de validada: o contrato recebe dígitos
  .transform((valor) => ({ ...valor, document: apenasDigitos(valor.document) }));

export type UserForm = z.infer<typeof userSchema>;
export type UserFormInput = z.input<typeof userSchema>;
