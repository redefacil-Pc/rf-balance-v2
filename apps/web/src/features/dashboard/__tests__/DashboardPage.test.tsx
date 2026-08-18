import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DashboardPage } from '@/features/dashboard/pages/DashboardPage';

vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({
    usuario: { full_name: 'Administrador Teste' },
    pode: () => true,
  }),
}));

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('DashboardPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('apresenta os indicadores, evolução e ranking reais', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({
      period_start: '2026-08-01',
      period_end: '2026-08-18',
      summary: {
        proposal_count: 8,
        open_count: 2,
        partially_paid_count: 1,
        paid_count: 5,
        cancelled_count: 0,
        pending_approval_count: 1,
        approved_production: '100000.00',
        company_commission: '30000.00',
        recognized_revenue: '10000.00',
        total_commissions: '1200.00',
        net_revenue: '8800.00',
        outstanding_amount: '20000.00',
        average_tps: '31.500000',
      },
      trend: [{
        business_date: '2026-08-17', proposal_count: 3,
        production_amount: '45000.00', recognized_revenue: '6000.00',
      }],
      ranking: [{
        collaborator_id: 10, collaborator_name: 'Carla Consultora',
        proposal_count: 4, production_amount: '60000.00',
      }],
    }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MantineProvider>
        <QueryClientProvider client={client}>
          <MemoryRouter><DashboardPage /></MemoryRouter>
        </QueryClientProvider>
      </MantineProvider>,
    );

    expect(await screen.findByText('R$ 100.000,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 8.800,00')).toBeInTheDocument();
    expect(screen.getByText('31,50%')).toBeInTheDocument();
    expect(screen.getByText('Carla Consultora')).toBeInTheDocument();
    expect(screen.getByText('1 aguardando aprovação')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Relatório financeiro' })).toBeInTheDocument();
  });
});
