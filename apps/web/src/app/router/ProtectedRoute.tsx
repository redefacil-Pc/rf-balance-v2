import { Center, Loader } from '@mantine/core';
import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '@/app/providers/AuthProvider';
import { SemPermissao } from '@/shared/components/SemPermissao';

interface Props {
  children: ReactNode;
  /** Permissão exigida para ver a tela. Esconder não é autorizar: o backend valida de novo. */
  permissao?: string;
}

export function ProtectedRoute({ children, permissao }: Props) {
  const { usuario, carregando, pode } = useAuth();
  const location = useLocation();

  if (carregando) {
    return (
      <Center mih="60vh">
        <Loader aria-label="Carregando" />
      </Center>
    );
  }

  if (!usuario) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (permissao && !pode(permissao)) {
    return <SemPermissao permissao={permissao} />;
  }

  return <>{children}</>;
}
