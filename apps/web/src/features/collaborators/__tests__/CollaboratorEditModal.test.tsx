import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CollaboratorEditModal } from '@/features/collaborators/components/CollaboratorEditModal';
import type { Collaborator } from '@/shared/types/organization';

const collaborator: Collaborator = {
  id: 1,
  full_name: 'Carla Consultora',
  company_id: 1,
  unit_id: 7,
  tax_regime: 'MEI',
  is_active: true,
  roles: ['CONSULTOR'],
  document: '***.***.350-**',
  document_type: 'CPF',
  user_id: 10,
};

function json(data: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('CollaboratorEditModal — modalidade', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it('troca o regime e a função para consultor escalonado no mesmo salvamento', async () => {
    let body: Record<string, unknown> | undefined;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      const path = String(url);
      if (init?.method === 'PUT') {
        body = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(json(null, 204));
      }
      if (path.includes('/collaborators/1/functions')) return Promise.resolve(json([
        { id: 20, role: 'CONSULTOR', valid_from: '2026-01-01', valid_to: null, current: true },
      ]));
      if (path.includes('/collaborators/1')) return Promise.resolve(json({
        id: 1, email: 'carla@rfbalance.local', phone: null, user_id: 10,
        payment_key_type: null, payment_key_masked: null,
      }));
      if (path.includes('/companies')) return Promise.resolve(json([
        { id: 1, legal_name: 'Rede Fácil', trade_name: 'Rede Fácil', is_active: true },
      ]));
      if (path.includes('/units')) return Promise.resolve(json([
        { id: 7, company_id: 1, code: 'MATRIZ', name: 'Matriz', is_active: true },
      ]));
      return Promise.resolve(json({}, 404));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MantineProvider><QueryClientProvider client={client}>
      <CollaboratorEditModal collaborator={collaborator} onClose={() => undefined} />
    </QueryClientProvider></MantineProvider>);
    const user = userEvent.setup();

    await user.click(await screen.findByRole('textbox', { name: /^regime$/i }));
    await user.click(await screen.findByRole('option', { name: 'CLT' }));
    await user.click(await screen.findByRole('textbox', { name: /regra de comissão/i }));
    await user.click(await screen.findByRole('option', { name: /Consultor escalonado/i }));
    await user.type(screen.getByLabelText(/motivo da alteração/i), 'Mudança aprovada');
    await user.click(screen.getByRole('button', { name: /salvar alterações/i }));

    await waitFor(() => expect(body).toBeDefined());
    expect(body).toMatchObject({
      tax_regime: 'CLT',
      consultant_modality: 'CONSULTOR_MEI_ESCALONADO',
      modality_reason: 'Mudança aprovada',
    });
    expect(body?.modality_valid_from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('usa a função vigente detalhada quando o resumo da tabela está desatualizado', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.includes('/collaborators/1/functions')) return Promise.resolve(json([
        { id: 20, role: 'CONSULTOR', valid_from: '2026-01-01', valid_to: null, current: true },
      ]));
      if (path.includes('/collaborators/1')) return Promise.resolve(json({
        id: 1, email: 'carla@rfbalance.local', phone: null, user_id: 10,
        payment_key_type: null, payment_key_masked: null,
      }));
      if (path.includes('/companies')) return Promise.resolve(json([]));
      if (path.includes('/units')) return Promise.resolve(json([]));
      return Promise.resolve(json({}, 404));
    });
    const staleCollaborator = { ...collaborator, roles: [] };
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MantineProvider><QueryClientProvider client={client}>
      <CollaboratorEditModal collaborator={staleCollaborator} onClose={() => undefined} />
    </QueryClientProvider></MantineProvider>);

    expect(await screen.findByRole('textbox', { name: /regra de comissão/i })).toBeInTheDocument();
  });
});
