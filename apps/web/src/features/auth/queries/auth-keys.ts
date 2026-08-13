/** Query keys da feature. Hierárquicas, para invalidação por prefixo. */
export const authKeys = {
  todos: ['auth'] as const,
  me: () => [...authKeys.todos, 'me'] as const,
};
