import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { UsersPage } from '@/features/users/pages/UsersPage';

vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({ usuario: { id: 99 }, pode: () => true, carregando: false }),
}));

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } });
}

describe('UsersPage', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.includes('/users/roles')) {
        return Promise.resolve(json([
          { code: 'OPERACIONAL', name: 'Operacional', permissions: ['proposals:write'] },
        ]));
      }
      if (path.includes('/companies')) {
        return Promise.resolve(json([
          { id: 1, legal_name: 'RF Balance LTDA', trade_name: 'RF Balance', is_active: true },
        ]));
      }
      if (path.includes('/units')) return Promise.resolve(json([]));
      if (path.includes('/users')) return Promise.resolve(json({ items: [], next_cursor: null }));
      return Promise.resolve(json({}));
    });
  });

  afterEach(() => vi.mocked(globalThis.fetch).mockRestore());

  async function abrirFormulario() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MantineProvider>
        <QueryClientProvider client={client}>
          <UsersPage />
        </QueryClientProvider>
      </MantineProvider>,
    );
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole('button', { name: /novo usuário/i }));
    await screen.findByLabelText(/nome completo/i);
    return usuario;
  }

  it('abre a criação conjunta de conta, acesso e função', async () => {
    await abrirFormulario();

    expect(await screen.findByLabelText(/nome completo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^e-mail/i)).toBeInTheDocument();
    expect(screen.getAllByLabelText(/perfis de acesso/i).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/^função/i).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/cpf ou cnpj/i)).toBeInTheDocument();
  });

  it('esconde o cadastro operacional para quem só usa o sistema', async () => {
    // administração e financeiro não são colaboradores comissionados: exigir
    // CPF e função deles obrigaria a inventar dado que suja a comissão depois
    const usuario = await abrirFormulario();

    await usuario.click(screen.getByLabelText(/também é colaboradora/i));

    expect(screen.queryByLabelText(/cpf ou cnpj/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^função/i)).not.toBeInTheDocument();
    // o que define acesso continua lá
    expect(screen.getAllByLabelText(/perfis de acesso/i).length).toBeGreaterThan(0);
  });
});
