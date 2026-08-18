import type { ProposalFilters } from '@/features/proposals/queries/useProposals';

/** Query keys hierárquicas: invalidação por prefixo depois das mutações. */
export const proposalKeys = {
  todos: ['proposals'] as const,
  lista: (filtros: ProposalFilters) => [...proposalKeys.todos, 'list', filtros] as const,
  detalhe: (id: number) => [...proposalKeys.todos, 'detail', id] as const,
  recebimentos: (id: number) => [...proposalKeys.todos, 'receipts', id] as const,
};
