import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '@/app/providers/AuthProvider';
import { ProposalApprovalModal } from '../components/ProposalApprovalModal';
import type { Proposal, ProposalDetail } from '@/shared/types/commercial';

const proposta: Proposal = {
  id: 8,
  external_id: 'DEMO-8',
  business_date: '2026-08-20',
  customer_name: 'Mercado Boa Compra',
  customer_document: '529.982.247-25',
  consultant_id: 2,
  consultant_name: 'Carla Consultora',
  bko_collaborator_id: null,
  finalizer_collaborator_id: 3,
  operation_amount: '18500.00',
  tps_percentage: '12.500000',
  company_commission_amount: '2312.50',
  paid_amount: '0.00',
  outstanding_amount: '2312.50',
  status: 'OPEN',
  approval_status: 'SUBMITTED',
  version: 2,
};

const detalhe: ProposalDetail = {
  ...proposta,
  bko_collaborator_name: null,
  finalizer_collaborator_name: 'Ana Operacional',
  overpaid: false,
  tolerance_policy_version: 'v1',
  rejection_reason: null,
  submitted_at: '2026-08-20T12:00:00Z',
  decided_at: null,
  settled_at: null,
  cancelled_at: null,
  cancellation_reason: null,
  timeline: [
    {
      action: 'proposal.created',
      occurred_at: '2026-08-20T11:00:00Z',
      actor_name: 'Ana Operacional',
      payload: {},
    },
    {
      action: 'proposal.submitted',
      occurred_at: '2026-08-20T12:00:00Z',
      actor_name: 'Ana Operacional',
      payload: {},
    },
  ],
};

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('ProposalApprovalModal', () => {
  afterEach(() => vi.restoreAllMocks());

  it('mostra o contexto e exige confirmação antes de aprovar', async () => {
    const requests: Array<{ url: string; method: string }> = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      const path = String(url);
      const method = init?.method ?? 'GET';
      requests.push({ url: path, method });
      if (path.endsWith('/auth/me')) {
        return Promise.resolve(json({
          id: 7,
          email: 'financeiro@rfbalance.local',
          full_name: 'Financeiro',
          roles: ['FINANCEIRO'],
          permissions: ['proposals:read', 'proposals:read_pii', 'proposals:approve', 'receipts:read'],
          must_change_password: false,
        }));
      }
      if (path.endsWith('/proposals/8')) return Promise.resolve(json(detalhe));
      if (path.includes('/receipts?proposal_id=8')) {
        return Promise.resolve(json({ items: [{
          id: 19,
          proposal_id: 8,
          proposal_approval_status: 'SUBMITTED',
          customer_name: proposta.customer_name,
          amount: '2312.50',
          business_date: '2026-08-20',
          payment_datetime: '2026-08-20T14:30:00Z',
          payment_method: 'PIX',
          receiving_account_id: 1,
          receiving_account_label: 'Conta de homologação',
          reference: 'DEMO-8',
          notes: null,
          status: 'SUBMITTED',
          rejection_reason: null,
          proof_file_name: 'comprovante.pdf',
          created_at: '2026-08-20T14:31:00Z',
          created_by: 3,
          creator_name: 'Ana Operacional',
          decided_at: null,
          decided_by: null,
          reversed: false,
          reversed_amount: '0.00',
          net_amount: '2312.50',
          reversal_reason: null,
        }] }));
      }
      if (path.endsWith('/proposals/8/decision') && method === 'POST') {
        return Promise.resolve(json({
          id: 8, approval_status: 'APPROVED', rejection_reason: null, version: 3,
        }));
      }
      throw new Error(`Requisição inesperada: ${method} ${path}`);
    });

    const onDecidida = vi.fn();
    render(
      <MantineProvider>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <AuthProvider>
            <ProposalApprovalModal proposta={proposta} onFechar={vi.fn()} onDecidida={onDecidida} />
          </AuthProvider>
        </QueryClientProvider>
      </MantineProvider>,
    );

    expect((await screen.findAllByText('Ana Operacional')).length).toBeGreaterThan(0);
    expect(screen.getByText('Conta de homologação')).toBeInTheDocument();
    expect(screen.getByText('Enviada ao Financeiro')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Aprovar e reconhecer valores' }));
    expect((await screen.findAllByText('Confirmar aprovação')).length).toBeGreaterThan(0);
    expect(requests.filter((item) => item.url.endsWith('/decision'))).toHaveLength(0);

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar aprovação' }));
    await waitFor(() => expect(onDecidida).toHaveBeenCalledWith(8));
    expect(requests.filter((item) => item.url.endsWith('/decision'))).toHaveLength(1);
  });
});
