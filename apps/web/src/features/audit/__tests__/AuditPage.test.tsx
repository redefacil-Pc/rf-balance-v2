import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuditPage } from '@/features/audit/pages/AuditPage';

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('AuditPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('lista a trilha e abre o contexto sem expor dados fora do evento', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (String(url).includes('/options')) {
        return Promise.resolve(json({
          modules: ['commercial'], actions: ['proposal.created'], aggregate_types: ['proposal'],
        }));
      }
      return Promise.resolve(json({
        items: [{
          id: 1,
          occurred_at: '2026-08-18T13:30:00Z',
          business_date: '2026-08-18',
          module: 'commercial',
          action: 'proposal.created',
          actor_user_id: 1,
          actor_name: 'Administrador Teste',
          aggregate_type: 'proposal',
          aggregate_id: '42',
          correlation_id: 'abc123456789',
          payload: { reason: 'Cadastro inicial' },
        }],
        next_cursor: null,
      }));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MantineProvider>
        <QueryClientProvider client={client}><AuditPage /></QueryClientProvider>
      </MantineProvider>,
    );

    expect(await screen.findByText('Administrador Teste')).toBeInTheDocument();
    expect(screen.getByText('proposal #42')).toBeInTheDocument();
    expect(screen.getByText('abc12345')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Detalhar' }));
    expect(await screen.findByText(/Cadastro inicial/)).toBeInTheDocument();
    expect(screen.getByText('abc123456789')).toBeInTheDocument();
  });
});
