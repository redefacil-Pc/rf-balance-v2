import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { BkoEntryModal, FinalizationEntryModal } from '@/features/settlements/components/BkoEntryModal';

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('BkoEntryModal', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it('lista BKO MEI mesmo sem conta de acesso e envia o valor sem máscara', async () => {
    let body: Record<string, unknown> | undefined;
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      const path = String(url);
      if (path.includes('/collaborators?')) {
        return Promise.resolve(json({
          items: [{
            id: 10,
            full_name: 'Gisele BKO',
            company_id: 1,
            unit_id: 1,
            tax_regime: 'MEI',
            is_active: true,
            roles: ['BKO'],
            document: '***.***.940-**',
            document_type: 'CPF',
            user_id: null,
          }],
          next_cursor: null,
        }));
      }
      if (path.includes('/commission-bko-entries') && init?.method === 'POST') {
        body = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(json({ id: 1 }, 201));
      }
      return Promise.resolve(json({}, 404));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MantineProvider>
        <QueryClientProvider client={client}>
          <BkoEntryModal opened onClose={() => undefined} />
        </QueryClientProvider>
      </MantineProvider>,
    );
    const user = userEvent.setup();

    await user.click(await screen.findByRole('textbox', { name: 'BKO MEI' }));
    await user.click(await screen.findByRole('option', { name: 'Gisele BKO' }));
    await user.type(screen.getByRole('textbox', { name: 'Valor' }), '12345');
    expect(screen.getByRole('textbox', { name: 'Valor' })).toHaveValue('123,45');
    await user.click(screen.getByRole('button', { name: 'Lançar' }));

    await waitFor(() => expect(body?.amount).toBe('123.45'));
    const calledUrl = fetchSpy.mock.calls.find(([url]) => String(url).includes('/collaborators?'));
    expect(String(calledUrl?.[0])).toContain('role=BKO');
    expect(String(calledUrl?.[0])).toContain('tax_regime=MEI');
    expect(String(calledUrl?.[0])).not.toContain('linked_user_only=true');
  });

  it('lista Finalização CLT ou MEI e registra como bônus manual', async () => {
    let body: Record<string, unknown> | undefined;
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      const path = String(url);
      if (path.includes('/collaborators?')) {
        return Promise.resolve(json({
          items: [{
            id: 12,
            full_name: 'Ana Finalizadora',
            company_id: 1,
            unit_id: 1,
            tax_regime: 'CLT',
            is_active: true,
            roles: ['FINALIZACAO'],
            document: '***.***.247-**',
            document_type: 'CPF',
            user_id: null,
          }],
          next_cursor: null,
        }));
      }
      if (path.includes('/commission-finalization-entries') && init?.method === 'POST') {
        body = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(json({ id: 2 }, 201));
      }
      return Promise.resolve(json({}, 404));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MantineProvider>
        <QueryClientProvider client={client}>
          <FinalizationEntryModal opened onClose={() => undefined} />
        </QueryClientProvider>
      </MantineProvider>,
    );
    const user = userEvent.setup();

    await user.click(await screen.findByRole('textbox', { name: 'Finalização' }));
    await user.click(await screen.findByRole('option', { name: 'Ana Finalizadora' }));
    await user.type(screen.getByRole('textbox', { name: 'Valor' }), '30000');
    await user.click(screen.getByRole('button', { name: 'Lançar' }));

    await waitFor(() => expect(body?.amount).toBe('300.00'));
    const calledUrl = fetchSpy.mock.calls.find(([url]) => String(url).includes('/collaborators?'));
    expect(String(calledUrl?.[0])).toContain('role=FINALIZACAO');
    expect(String(calledUrl?.[0])).not.toContain('tax_regime=');
  });
});
