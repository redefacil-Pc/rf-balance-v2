import { createContext, useContext, useMemo, type ReactNode } from 'react';

import { useCurrentUser } from '@/features/auth/queries/useCurrentUser';
import type { CurrentUser } from '@/shared/types/current-user';

interface AuthContexto {
  usuario: CurrentUser | null;
  carregando: boolean;
  /** Conveniência de UI. A autorização de verdade é do backend. */
  pode: (permissao: string) => boolean;
}

const Contexto = createContext<AuthContexto | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isLoading } = useCurrentUser();

  const valor = useMemo<AuthContexto>(() => {
    const permissoes = new Set(data?.permissions ?? []);
    return {
      usuario: data ?? null,
      carregando: isLoading,
      pode: (permissao) => permissoes.has(permissao),
    };
  }, [data, isLoading]);

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAuth(): AuthContexto {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error('useAuth precisa estar dentro de AuthProvider');
  }
  return contexto;
}
