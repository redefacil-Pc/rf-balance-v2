import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CollaboratorAccountModal } from '@/features/collaborators/components/CollaboratorAccountModal';
import type { Collaborator } from '@/shared/types/organization';

const collaborator: Collaborator = {
  id: 14,
  full_name: 'Carla Consultora',
  company_id: 1,
  unit_id: 1,
  tax_regime: 'CLT',
  is_active: true,
  roles: ['CONSULTOR'],
  document: '***.***.350-**',
  document_type: 'CPF',
  user_id: 16,
  user_full_name: 'Carla Conta',
  user_email: 'carla@rfbalance.local',
  user_is_active: true,
};

function json(data: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('CollaboratorAccountModal', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it('troca a conta vinculada por outra conta ativa', async () => {
    let body: Record<string, unknown> | undefined;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      const path = String(url);
      if (init?.method === 'PUT' && path.includes('/collaborators/14/account')) {
        body = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(json(null, 204));
      }
      if (path.includes('/users?')) return Promise.resolve(json({
        items: [{
          id: 20,
          email: 'nova@rfbalance.local',
          full_name: 'Nova Conta',
          roles: ['CONSULTOR'],
          is_active: true,
        }],
        next_cursor: null,
      }));
      return Promise.resolve(json({}, 404));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MantineProvider><QueryClientProvider client={client}>
      <CollaboratorAccountModal collaborator={collaborator} onClose={() => undefined} />
    </QueryClientProvider></MantineProvider>);
    const user = userEvent.setup();

    await user.click(await screen.findByRole('textbox', { name: /conta vinculada/i }));
    await user.click(await screen.findByRole('option', { name: /Nova Conta/i }));
    await user.click(screen.getByRole('button', { name: /salvar vínculo/i }));

    await waitFor(() => expect(body).toEqual({ user_id: 20 }));
  });
});
