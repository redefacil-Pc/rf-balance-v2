import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CommissionExplanationModal } from '@/features/receipts/components/CommissionExplanationModal';

describe('CommissionExplanationModal', () => {
  afterEach(() => vi.restoreAllMocks());

  it('carrega a memória consolidada pela proposta', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      items: [{
        id: 8,
        proposal_id: 42,
        receipt_id: 19,
        beneficiary_id: 3,
        beneficiary_name: 'Carla Consultora',
        strategy: 'STANDARD_CONSULTANT',
        rule_version: '2026.1',
        competence_date: '2026-08-17',
        inputs: { receipt_eligible_amount: '400.00', tps: '35.000000' },
        outputs: { percentage: '12.000000', commission_amount: '48.00' },
        calculated_at: '2026-08-17T15:00:00Z',
        entries: [{
          id: 9,
          entry_type: 'CREDIT',
          amount: '48.00',
          competence_date: '2026-08-17',
          description: 'Comissão de consultor padrão',
          reversal_id: null,
          created_at: '2026-08-17T15:00:00Z',
        }],
        net_amount: '48.00',
      }],
      total_net_amount: '48.00',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <MantineProvider>
        <QueryClientProvider client={client}>
          <CommissionExplanationModal proposalId={42} onClose={() => undefined} />
        </QueryClientProvider>
      </MantineProvider>,
    );

    expect(await screen.findByText('Proposta #42')).toBeInTheDocument();
    expect(screen.getByText(/Total líquido:/)).toHaveTextContent('R$ 48,00');
    await userEvent.click(screen.getByText('Consultor padrão'));
    expect(await screen.findByText('35%')).toBeInTheDocument();
    expect(screen.getByText('12%')).toBeInTheDocument();
    expect(screen.queryByText(/35,000000%|12,000000%/)).not.toBeInTheDocument();
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    expect(String(fetchSpy.mock.calls[0]?.[0])).toContain(
      '/proposals/42/commission-calculations',
    );
  });
});
