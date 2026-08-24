import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter } from 'react-router-dom';

import { AppLayout } from '@/app/layouts/AppLayout';
import { NotFoundPage } from '@/app/router/NotFoundPage';
import { ProtectedRoute } from '@/app/router/ProtectedRoute';
import { RouteErrorPage } from '@/app/router/RouteErrorPage';
import { routeModules } from '@/app/router/route-modules';
import { ContentLoading } from '@/shared/components/ContentLoading';

const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage').then((module) => ({ default: module.LoginPage })));
const OperationsPage = lazy(() => routeModules['/admin/operations']().then((module) => ({ default: module.OperationsPage })));
const AuditPage = lazy(() => routeModules['/audit']().then((module) => ({ default: module.AuditPage })));
const CollaboratorsPage = lazy(() => routeModules['/collaborators']().then((module) => ({ default: module.CollaboratorsPage })));
const CommissionRulesPage = lazy(() => routeModules['/commission-rules']().then((module) => ({ default: module.CommissionRulesPage })));
const DashboardPage = lazy(() => routeModules['/']().then((module) => ({ default: module.DashboardPage })));
const ProposalsPage = lazy(() => routeModules['/proposals']().then((module) => ({ default: module.ProposalsPage })));
const ProposalApprovalsPage = lazy(() => routeModules['/proposal-approvals']().then((module) => ({ default: module.ProposalApprovalsPage })));
const PeriodsPage = lazy(() => routeModules['/periods']().then((module) => ({ default: module.PeriodsPage })));
const ReceiptsPage = lazy(() => routeModules['/receipts']().then((module) => ({ default: module.ReceiptsPage })));
const FinancialReportPage = lazy(() => routeModules['/reports']().then((module) => ({ default: module.FinancialReportPage })));
const SettlementsPage = lazy(() => routeModules['/settlements']().then((module) => ({ default: module.SettlementsPage })));
const TeamsPage = lazy(() => routeModules['/teams']().then((module) => ({ default: module.TeamsPage })));
const ReceivingAccountsPage = lazy(() => routeModules['/receiving-accounts']().then((module) => ({ default: module.ReceivingAccountsPage })));
const UnitsPage = lazy(() => routeModules['/units']().then((module) => ({ default: module.UnitsPage })));
const UsersPage = lazy(() => routeModules['/admin/users']().then((module) => ({ default: module.UsersPage })));

function withPageLoading(page: ReactNode): ReactNode {
  return (
    <Suspense fallback={<ContentLoading label="Carregando página" minHeight={360} />}>
      {page}
    </Suspense>
  );
}

export const router = createBrowserRouter([
  { path: '/login', element: withPageLoading(<LoginPage />), errorElement: <RouteErrorPage /> },
  {
    path: '/',
    errorElement: <RouteErrorPage />,
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
            {withPageLoading(<DashboardPage />)}
          </ProtectedRoute>
        ),
      },
      // ---------- F2: entregues ----------
      {
        path: '/collaborators',
        element: (
          <ProtectedRoute permissao="collaborators:read">
            {withPageLoading(<CollaboratorsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/proposals',
        element: (
          <ProtectedRoute permissao="proposals:read">
            {withPageLoading(<ProposalsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/proposal-approvals',
        element: (
          <ProtectedRoute permissao="proposals:approve">
            {withPageLoading(<ProposalApprovalsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/receipts',
        element: (
          <ProtectedRoute permissao="receipts:read">
            {withPageLoading(<ReceiptsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/teams',
        element: (
          <ProtectedRoute permissao="teams:read">
            {withPageLoading(<TeamsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/admin/users',
        element: (
          <ProtectedRoute permissao="users:read">
            {withPageLoading(<UsersPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/admin/operations',
        element: (
          <ProtectedRoute permissao="admin:operations">
            {withPageLoading(<OperationsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/units',
        element: (
          <ProtectedRoute permissao="collaborators:read">
            {withPageLoading(<UnitsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/receiving-accounts',
        element: (
          <ProtectedRoute permissao="receipts:read">
            {withPageLoading(<ReceivingAccountsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/commission-rules',
        element: (
          <ProtectedRoute permissao="commission_rules:read">
            {withPageLoading(<CommissionRulesPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/settlements',
        element: (
          <ProtectedRoute permissao="settlements:read">
            {withPageLoading(<SettlementsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/periods',
        element: (
          <ProtectedRoute permissao="periods:read">
            {withPageLoading(<PeriodsPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/audit',
        element: (
          <ProtectedRoute permissao="audit:read">
            {withPageLoading(<AuditPage />)}
          </ProtectedRoute>
        ),
      },
      {
        path: '/reports',
        element: (
          <ProtectedRoute permissao="settlements:read">
            {withPageLoading(<FinancialReportPage />)}
          </ProtectedRoute>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
