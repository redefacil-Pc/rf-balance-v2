import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ReceivingAccountsPage } from '@/features/receiving-accounts/pages/ReceivingAccountsPage';

const conta = (id: number, label: string, ordem: number, ativa = true) => ({
  id,
  label,
  display_order: ordem,
  is_active: ativa,
  created_at: '2026-08-18T12:00:00Z',
  updated_at: '2026-08-18T12:00:00Z',
});

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({ pode: () => true }),
}));

describe('ReceivingAccountsPage', () => {
  afterEach(() => vi.restoreAllMocks());

  function montar() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MantineProvider>
        <QueryClientProvider client={client}>
          <ReceivingAccountsPage />
        </QueryClientProvider>
      </MantineProvider>,
    );
    return userEvent.setup();
  }

  it('cadastra uma conta nova pelo campo do topo', async () => {
    let body: Record<string, unknown> | undefined;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      if (String(url).includes('/receiving-accounts') && init?.method === 'POST') {
        body = JSON.parse(String(init.body)) as Record<string, unknown>;
        return Promise.resolve(json(conta(3, 'Conta Fábio (BANCO DO BRASIL)', 3), 201));
      }
      return Promise.resolve(json([conta(1, 'Almeida Serviços LTDA (SANTANDER)', 1)]));
    });
    const user = montar();

    await user.type(
      await screen.findByRole('textbox', { name: /Nova conta bancária/ }),
      'Conta Fábio (BANCO DO BRASIL)',
    );
    await user.click(screen.getByRole('button', { name: 'Adicionar' }));

    await waitFor(() => expect(body?.label).toBe('Conta Fábio (BANCO DO BRASIL)'));
    // sem ordem no corpo: quem decide a posição de uma conta nova é o servidor
    expect(body).not.toHaveProperty('display_order');
  });

  it('só habilita Salvar na linha que foi alterada', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        json([
          conta(1, 'Almeida Serviços LTDA (SANTANDER)', 1),
          conta(2, 'Conta PF Fábio (BRADESCO)', 2),
        ]),
      ),
    );
    const user = montar();

    const primeira = await screen.findByDisplayValue('Almeida Serviços LTDA (SANTANDER)');
    const salvar = screen.getAllByRole('button', { name: 'Salvar' });
    expect(salvar[0]).toBeDisabled();
    expect(salvar[1]).toBeDisabled();

    await user.type(primeira, ' II');

    expect(screen.getAllByRole('button', { name: 'Salvar' })[0]).toBeEnabled();
    expect(screen.getAllByRole('button', { name: 'Salvar' })[1]).toBeDisabled();
  });

  it('mostra a conta desativada como inativa, sem sumir do cadastro', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(json([conta(2, 'Conta PF Fábio (BRADESCO)', 2, false)])),
    );
    montar();

    expect(await screen.findByText('Inativa')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reativar' })).toBeInTheDocument();
  });
});
