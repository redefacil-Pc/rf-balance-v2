import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { FinancialReportPage } from '@/features/reports/pages/FinancialReportPage';

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

const summary = {
  gross_revenue: '1000.00', receipt_reversals: '100.00', recognized_revenue: '900.00',
  recognized_production: '5000.00', consultant_commissions: '60.00', leader_commissions: '10.00',
  finalization_commissions: '300.00', finalization_leader_commissions: '5.00',
  bko_commissions: '100.00', total_commissions: '475.00', net_billing: '425.00',
  bonuses: '300.00', discounts: '20.00', deferred: '100.00', paid: '200.00', payable: '455.00',
};

describe('FinancialReportPage', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it('mostra consolidado e abre a origem do valor do beneficiário', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (String(url).includes('/document-jobs')) return Promise.resolve(json({ items: [] }));
      if (String(url).includes('/beneficiaries/10')) {
        return Promise.resolve(json({
          summary: {
            recognized_production: '0.00', received_amount: '0.00',
            commission_amount: '100.00', deferred_amount: '0.00',
          },
          items: [{
          source: 'MANUAL', strategy: 'BKO', entry_type: 'BKO_COMMISSION',
          competence_date: '2026-08-17', amount: '100.00', description: 'Comissão BKO',
          proposal_id: null, proposal_external_id: null, customer_name: null, receipt_id: null,
          recognized_production: '0.00', received_amount: '0.00',
          received_percentage: null, tps_percentage: null,
        }],
        }));
      }
      return Promise.resolve(json({
        period_start: '2026-08-14', period_end: '2026-08-20', summary,
        beneficiaries: [{
          beneficiary_id: 10, beneficiary_name: 'Gisele BKO', strategies: ['BKO'],
          automatic_amount: '0.00', manual_amount: '100.00', calculated_amount: '100.00',
          carryover_amount: '0.00', bonus_amount: '0.00', discount_amount: '0.00',
          deferred_amount: '0.00', paid_amount: '0.00', payable_amount: '100.00', status: 'PENDING',
        }],
      }));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MantineProvider><QueryClientProvider client={client}>
      <FinancialReportPage />
    </QueryClientProvider></MantineProvider>);

    expect(await screen.findByText('Gisele BKO')).toBeInTheDocument();
    expect(screen.getByText('R$ 425,00')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Consultores' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Finalização' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'BKO' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Lideranças' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Detalhar' }));
    expect(await screen.findByText('Comissão BKO')).toBeInTheDocument();
    expect(screen.getAllByText('Manual')).toHaveLength(2);
  });

  it('aplica o recorte de unidade também na consulta do relatório', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const value = String(url);
      if (value.includes('/document-jobs')) return Promise.resolve(json({ items: [] }));
      if (value.includes('/units?')) {
        return Promise.resolve(json([{
          id: 7, company_id: 1, code: 'SP', name: 'São Paulo', is_active: true,
        }]));
      }
      if (value.includes('/assignments/active?')) return Promise.resolve(json([]));
      return Promise.resolve(json({
        period_start: '2026-08-14', period_end: '2026-08-20', summary,
        beneficiaries: [],
      }));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MantineProvider><QueryClientProvider client={client}>
      <FinancialReportPage />
    </QueryClientProvider></MantineProvider>);

    await userEvent.click(screen.getByText('Por unidade'));
    await userEvent.click(await screen.findByRole('textbox', { name: 'Unidade' }));
    await userEvent.click(await screen.findByText('SP · São Paulo'));

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('unit_id=7'),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('mostra o progresso concluído e disponibiliza o ZIP do lote', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const value = String(url);
      if (value.includes('/document-jobs')) return Promise.resolve(json({ items: [{
        id: 44, job_type: 'COMMISSION_REPORT_BATCH', status: 'COMPLETED',
        period_start: '2026-08-14', period_end: '2026-08-20', unit_id: null, leader_id: null,
        total_items: 5, processed_items: 5, attempt_count: 1, max_attempts: 3,
        error_message: null, archive_ready: true, created_at: '2026-08-20T12:00:00Z',
        started_at: '2026-08-20T12:00:01Z', completed_at: '2026-08-20T12:00:03Z',
      }] }));
      if (value.includes('/units?') || value.includes('/assignments/active?')) {
        return Promise.resolve(json([]));
      }
      return Promise.resolve(json({
        period_start: '2026-08-14', period_end: '2026-08-20', summary,
        beneficiaries: [],
      }));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MantineProvider><QueryClientProvider client={client}>
      <FinancialReportPage />
    </QueryClientProvider></MantineProvider>);

    expect(await screen.findByText('Lote #44')).toBeInTheDocument();
    const download = screen.getByRole('link', { name: 'Baixar ZIP' });
    expect(download).toHaveAttribute('href', '/api/v1/document-jobs/44/download');
    expect(screen.getByText('5 de 5 PDFs gerados')).toBeInTheDocument();
  });
});
