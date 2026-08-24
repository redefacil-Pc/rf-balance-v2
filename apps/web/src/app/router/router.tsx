import { Center, Loader } from '@mantine/core';
import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter } from 'react-router-dom';

import { AppLayout } from '@/app/layouts/AppLayout';
import { ProtectedRoute } from '@/app/router/ProtectedRoute';

const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage').then((module) => ({ default: module.LoginPage })));
const OperationsPage = lazy(() => import('@/features/operations/pages/OperationsPage').then((module) => ({ default: module.OperationsPage })));
const AuditPage = lazy(() => import('@/features/audit/pages/AuditPage').then((module) => ({ default: module.AuditPage })));
const CollaboratorsPage = lazy(() => import('@/features/collaborators/pages/CollaboratorsPage').then((module) => ({ default: module.CollaboratorsPage })));
const CommissionRulesPage = lazy(() => import('@/features/commission-rules/pages/CommissionRulesPage').then((module) => ({ default: module.CommissionRulesPage })));
const DashboardPage = lazy(() => import('@/features/dashboard/pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const ProposalsPage = lazy(() => import('@/features/proposals/pages/ProposalsPage').then((module) => ({ default: module.ProposalsPage })));
const ProposalApprovalsPage = lazy(() => import('@/features/proposals/pages/ProposalApprovalsPage').then((module) => ({ default: module.ProposalApprovalsPage })));
const PeriodsPage = lazy(() => import('@/features/periods/pages/PeriodsPage').then((module) => ({ default: module.PeriodsPage })));
const ReceiptsPage = lazy(() => import('@/features/receipts/pages/ReceiptsPage').then((module) => ({ default: module.ReceiptsPage })));
const FinancialReportPage = lazy(() => import('@/features/reports/pages/FinancialReportPage').then((module) => ({ default: module.FinancialReportPage })));
const SettlementsPage = lazy(() => import('@/features/settlements/pages/SettlementsPage').then((module) => ({ default: module.SettlementsPage })));
const TeamsPage = lazy(() => import('@/features/teams/pages/TeamsPage').then((module) => ({ default: module.TeamsPage })));
const ReceivingAccountsPage = lazy(() => import('@/features/receiving-accounts/pages/ReceivingAccountsPage').then((module) => ({ default: module.ReceivingAccountsPage })));
const UnitsPage = lazy(() => import('@/features/units/pages/UnitsPage').then((module) => ({ default: module.UnitsPage })));
const UsersPage = lazy(() => import('@/features/users/pages/UsersPage').then((module) => ({ default: module.UsersPage })));

function withPageLoading(page: ReactNode): ReactNode {
  return (
    <Suspense fallback={<Center mih="50vh"><Loader aria-label="Carregando página" /></Center>}>
      {page}
    </Suspense>
  );
}

export const router = createBrowserRouter([
  { path: '/login', element: withPageLoading(<LoginPage />) },
  {
    path: '/',
    element: withPageLoading(
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
        path: '/admin/operations',
        element: (
          <ProtectedRoute permissao="admin:operations">
            <OperationsPage />
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
        path: '/receiving-accounts',
        element: (
          <ProtectedRoute permissao="receipts:read">
            <ReceivingAccountsPage />
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
    ],
  },
]);
