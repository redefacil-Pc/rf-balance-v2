import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CollaboratorFunctionsModal } from '@/features/collaborators/components/CollaboratorFunctionsModal';
import type { Collaborator } from '@/shared/types/organization';

const carla: Collaborator = {
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
};

function json(data: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('CollaboratorFunctionsModal', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it('troca consultor padrão por escalonado preservando o cadastro', async () => {
    let body: Record<string, unknown> | undefined;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      const path = String(url);
      if (init?.method === 'PUT' && path.endsWith('/collaborators/14')) {
        body = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(json(null, 204));
      }
      if (path.includes('/collaborators/14/functions')) return Promise.resolve(json([
        { id: 30, role: 'CONSULTOR', valid_from: '2026-01-01', valid_to: null, current: true },
      ]));
      if (path.includes('/collaborators/14/details')) return Promise.resolve(json({
        id: 14,
        email: 'carla@rfbalance.local',
        phone: null,
        user_id: 16,
        payment_key_type: null,
        payment_key_masked: null,
      }));
      return Promise.resolve(json({}, 404));
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(<MantineProvider><QueryClientProvider client={client}>
      <CollaboratorFunctionsModal colaborador={carla} podeEscrever onFechar={() => undefined} />
    </QueryClientProvider></MantineProvider>);
    const user = userEvent.setup();

    await screen.findByText('Consultor padrão');
    await user.click(screen.getByRole('textbox', { name: /^função$/i }));
    await user.click(await screen.findByRole('option', { name: 'Consultor escalonado' }));
    await user.type(screen.getByLabelText(/motivo da troca/i), 'Mudança aprovada');
    await user.click(screen.getByRole('button', { name: 'Trocar' }));

    await waitFor(() => expect(body).toBeDefined());
    expect(body).toMatchObject({
      tax_regime: 'CLT',
      consultant_modality: 'CONSULTOR_MEI_ESCALONADO',
      modality_reason: 'Mudança aprovada',
    });
  });
});
