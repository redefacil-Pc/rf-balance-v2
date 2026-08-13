import { z } from 'zod';

import { apenasDigitos, temTamanhoDeDocumento } from '@/shared/formatters/document-mask';
import { moedaParaDecimal } from '@/shared/formatters/money-mask';
import { percentualParaDecimal } from '@/shared/formatters/percent-mask';

/**
 * Validação de forma no cliente. O dígito verificador do documento, a unicidade
 * do Redmine e o cálculo da comissão são do backend — aqui só evitamos o
 * ida-e-volta óbvio.
 *
 * Os campos chegam **mascarados**, como o operador os vê, e saem no formato do
 * contrato: dinheiro como string decimal (`"14629.64"`) e documento em dígitos.
 * A conversão é feita no `transform`, e é o único ponto onde a máscara some.
 * Nada vira `number` no caminho: centavo não sobrevive a ponto flutuante.
 */
const dinheiro = z
  .string()
  .min(1, 'Informe o valor da operação')
  .transform(moedaParaDecimal)
  .refine((valor) => Number(valor) > 0, 'O valor deve ser maior que zero');

const percentual = z
  .string()
  .min(1, 'Informe o TPS')
  .transform(percentualParaDecimal)
  .refine((valor) => /^\d+(\.\d{1,6})?$/.test(valor), 'Use o formato 12,5')
  .refine((valor) => Number(valor) <= 100, 'O TPS vai de 0 a 100');

export const proposalSchema = z.object({
  consultant_id: z.number({ required_error: 'Selecione o consultor' }).int().positive(),
  business_date: z.string().min(1, 'Informe a data de negócio'),
  customer_name: z
    .string()
    .min(3, 'Informe o nome do cliente')
    .max(200)
    .transform((valor) => valor.trim()),
  customer_document: z
    .string()
    .min(1, 'Informe o CPF ou CNPJ do cliente')
    .refine(temTamanhoDeDocumento, 'O documento deve ter 11 dígitos (CPF) ou 14 (CNPJ)')
    .transform(apenasDigitos),
  operation_amount: dinheiro,
  tps_percentage: percentual,
  external_id: z.string().max(60).optional(),
  bko_collaborator_id: z.number().int().positive().nullable(),
  finalizer_collaborator_id: z.number().int().positive().nullable(),
});

export type ProposalForm = z.infer<typeof proposalSchema>;

/** O que o formulário guarda — mascarado — antes do `transform`. */
export type ProposalFormEntrada = z.input<typeof proposalSchema>;

/**
 * Alteração cobre só o que o backend aceita mudar: valor, TPS e os participantes
 * de apoio. Cliente, consultor e data de negócio não se editam — proposta errada
 * se cancela e se cadastra de novo, para o histórico continuar contando a
 * verdade.
 */
export const updateProposalSchema = z.object({
  operation_amount: dinheiro,
  tps_percentage: percentual,
  bko_collaborator_id: z.number().int().positive().nullable(),
  finalizer_collaborator_id: z.number().int().positive().nullable(),
});

export type UpdateProposalForm = z.infer<typeof updateProposalSchema>;
export type UpdateProposalFormEntrada = z.input<typeof updateProposalSchema>;

export const cancelProposalSchema = z.object({
  reason: z.string().min(3, 'Explique o motivo do cancelamento').max(255),
});

export type CancelProposalForm = z.infer<typeof cancelProposalSchema>;
