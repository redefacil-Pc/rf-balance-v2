import { createBrowserRouter, type RouteObject } from 'react-router-dom';

import { AppLayout } from '@/app/layouts/AppLayout';
import { ProtectedRoute } from '@/app/router/ProtectedRoute';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { AuditPage } from '@/features/audit/pages/AuditPage';
import { CollaboratorsPage } from '@/features/collaborators/pages/CollaboratorsPage';
import { CommissionRulesPage } from '@/features/commission-rules/pages/CommissionRulesPage';
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage';
import { ProposalsPage } from '@/features/proposals/pages/ProposalsPage';
import { ProposalApprovalsPage } from '@/features/proposals/pages/ProposalApprovalsPage';
import { PeriodsPage } from '@/features/periods/pages/PeriodsPage';
import { ReceiptsPage } from '@/features/receipts/pages/ReceiptsPage';
import { FinancialReportPage } from '@/features/reports/pages/FinancialReportPage';
import { SettlementsPage } from '@/features/settlements/pages/SettlementsPage';
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
        path: '/proposal-approvals',
        element: (
          <ProtectedRoute permissao="proposals:approve">
            <ProposalApprovalsPage />
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
      {
        path: '/commission-rules',
        element: (
          <ProtectedRoute permissao="commission_rules:read">
            <CommissionRulesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/settlements',
        element: (
          <ProtectedRoute permissao="settlements:read">
            <SettlementsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/periods',
        element: (
          <ProtectedRoute permissao="periods:read">
            <PeriodsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/audit',
        element: (
          <ProtectedRoute permissao="audit:read">
            <AuditPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/reports',
        element: (
          <ProtectedRoute permissao="settlements:read">
            <FinancialReportPage />
          </ProtectedRoute>
        ),
      },
      ...rotasPendentes,
    ],
  },
]);
