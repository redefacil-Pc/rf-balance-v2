import { createBrowserRouter, type RouteObject } from 'react-router-dom';

import { AppLayout } from '@/app/layouts/AppLayout';
import { ProtectedRoute } from '@/app/router/ProtectedRoute';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { CollaboratorsPage } from '@/features/collaborators/pages/CollaboratorsPage';
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage';
import { ProposalsPage } from '@/features/proposals/pages/ProposalsPage';
import { ReceiptsPage } from '@/features/receipts/pages/ReceiptsPage';
import { TeamsPage } from '@/features/teams/pages/TeamsPage';
import { UnitsPage } from '@/features/units/pages/UnitsPage';
import { UsersPage } from '@/features/users/pages/UsersPage';
import { TelaPendente } from '@/shared/components/TelaPendente';

/**
 * Rotas da seção 10.3 do blueprint. Toda rota nasce protegida e com a permissão
 * declarada; as que dependem de fases seguintes mostram `TelaPendente` em vez de
 * dado simulado.
 */
interface Pendente {
  caminho: string;
  titulo: string;
  permissao: string;
  fase: string;
  descricao: string;
}

const pendentes: Pendente[] = [
  {
    caminho: '/commission-rules',
    titulo: 'Regras de comissão',
    permissao: 'commission_rules:read',
    fase: 'F4',
    descricao:
      'Conjuntos de regras versionados com vigência, sem lacuna nem sobreposição, e explicação do cálculo.',
  },
  {
    caminho: '/periods',
    titulo: 'Períodos',
    permissao: 'periods:read',
    fase: 'F5',
    descricao: 'Semanas, cutoff e fechamento. Período fechado fica imutável.',
  },
  {
    caminho: '/settlements',
    titulo: 'Fechamentos',
    permissao: 'settlements:read',
    fase: 'F5',
    descricao: 'Fechamento por beneficiário e período, aprovação e pagamento real.',
  },
  {
    caminho: '/reports',
    titulo: 'Relatórios',
    permissao: 'reports:read',
    fase: 'F6',
    descricao:
      'Relatórios individual, de equipe, unidade, geral e operacional, com exportação assíncrona em PDF, XLSX e ZIP.',
  },
  {
    caminho: '/audit',
    titulo: 'Auditoria',
    permissao: 'audit:read',
    fase: 'F6',
    descricao:
      'Consulta da trilha append-only: quem fez o quê, quando e com qual regra. A gravação já está ativa desde a F1.',
  },
  {
    caminho: '/admin/operations',
    titulo: 'Operações administrativas',
    permissao: 'admin:operations',
    fase: 'F6',
    descricao: 'Verificação de integridade, recálculo controlado e rotinas operacionais.',
  },
];

const rotasPendentes: RouteObject[] = pendentes.map((tela) => ({
  path: tela.caminho,
  element: (
    <ProtectedRoute permissao={tela.permissao}>
      <TelaPendente titulo={tela.titulo} fase={tela.fase} descricao={tela.descricao} />
    </ProtectedRoute>
  ),
}));

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: (
          <ProtectedRoute permissao="dashboard:read">
            <DashboardPage />
          </ProtectedRoute>
        ),
      },
      // ---------- F2: entregues ----------
      {
        path: '/collaborators',
        element: (
          <ProtectedRoute permissao="collaborators:read">
            <CollaboratorsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/proposals',
        element: (
          <ProtectedRoute permissao="proposals:read">
            <ProposalsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/receipts',
        element: (
          <ProtectedRoute permissao="receipts:read">
            <ReceiptsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/teams',
        element: (
          <ProtectedRoute permissao="teams:read">
            <TeamsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/admin/users',
        element: (
          <ProtectedRoute permissao="users:read">
            <UsersPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/units',
        element: (
          <ProtectedRoute permissao="collaborators:read">
            <UnitsPage />
          </ProtectedRoute>
        ),
      },
      ...rotasPendentes,
    ],
  },
]);
