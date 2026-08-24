export const ROTULO_DO_EVENTO: Record<string, string> = {
  'proposal.created': 'Proposta cadastrada',
  'proposal.updated': 'Dados atualizados',
  'proposal.submitted': 'Enviada ao Financeiro',
  'proposal.approved': 'Proposta aprovada',
  'proposal.rejected': 'Devolvida para correção',
  'proposal.cancelled': 'Proposta cancelada',
  'proposal.attachment_added': 'Documento adicionado',
  'proposal.attachment_removed': 'Documento removido',
};

export function formatarDataHora(valor: string | null): string {
  if (!valor) return 'Horário não informado';
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(valor));
}

export function formatarPercentual(valor: string): string {
  return `${Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 6 })}%`;
}

/** Soma decimal exata somente para apresentação; nunca usa ponto flutuante. */
export function somarValores(valores: string[]): string {
  const centavos = valores.reduce((total, valor) => {
    const [inteiro = '0', decimal = ''] = valor.split('.');
    return total + BigInt(inteiro) * 100n + BigInt(decimal.padEnd(2, '0').slice(0, 2));
  }, 0n);
  return `${centavos / 100n}.${(centavos % 100n).toString().padStart(2, '0')}`;
}
