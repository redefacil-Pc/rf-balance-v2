import type { CollaboratorFilters } from '@/features/collaborators/queries/useCollaborators';

/** Query keys hierárquicas: invalidação por prefixo depois das mutações. */
export const collaboratorKeys = {
  todos: ['collaborators'] as const,
  lista: (filtros: CollaboratorFilters) => [...collaboratorKeys.todos, 'list', filtros] as const,
  detalhe: (id: number) => [...collaboratorKeys.todos, 'detail', id] as const,
  funcoes: (id: number) => [...collaboratorKeys.todos, 'functions', id] as const,
  // literal, não derivada de `todos`: uma propriedade não pode se referenciar
  // dentro do próprio objeto que a define
  contasVinculaveis: ['collaborators', 'linkable-accounts'] as const,
};

export const organizationKeys = {
  empresas: ['companies'] as const,
  unidades: (companyId?: number) => ['units', companyId ?? 'todas'] as const,
};
