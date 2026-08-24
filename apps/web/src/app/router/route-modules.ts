const routeModules = {
  '/': () => import('@/features/dashboard/pages/DashboardPage'),
  '/admin/operations': () => import('@/features/operations/pages/OperationsPage'),
  '/admin/users': () => import('@/features/users/pages/UsersPage'),
  '/audit': () => import('@/features/audit/pages/AuditPage'),
  '/collaborators': () => import('@/features/collaborators/pages/CollaboratorsPage'),
  '/commission-rules': () => import('@/features/commission-rules/pages/CommissionRulesPage'),
  '/periods': () => import('@/features/periods/pages/PeriodsPage'),
  '/proposal-approvals': () => import('@/features/proposals/pages/ProposalApprovalsPage'),
  '/proposals': () => import('@/features/proposals/pages/ProposalsPage'),
  '/receipts': () => import('@/features/receipts/pages/ReceiptsPage'),
  '/receiving-accounts': () => import('@/features/receiving-accounts/pages/ReceivingAccountsPage'),
  '/reports': () => import('@/features/reports/pages/FinancialReportPage'),
  '/settlements': () => import('@/features/settlements/pages/SettlementsPage'),
  '/teams': () => import('@/features/teams/pages/TeamsPage'),
  '/units': () => import('@/features/units/pages/UnitsPage'),
} as const;

export function preloadRoute(pathname: string): void {
  const load = routeModules[pathname as keyof typeof routeModules];
  if (load) void load();
}

export { routeModules };
