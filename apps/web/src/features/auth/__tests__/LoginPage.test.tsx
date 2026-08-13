import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LoginPage } from '@/features/auth/pages/LoginPage';

function renderizar() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <MantineProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/login']}>
          <LoginPage />
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>,
  );
}

const respostaNaoAutenticado = () =>
  new Response(
    JSON.stringify({
      type: 'https://rfbalance/errors/session-invalid',
      title: 'Sessão inválida',
      status: 401,
      detail: 'Sessão ausente.',
      instance: '/api/v1/auth/me',
      correlation_id: 'abc123',
      errors: [],
    }),
    { status: 401, headers: { 'Content-Type': 'application/problem+json' } },
  );

describe('LoginPage', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaNaoAutenticado());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('apresenta os campos por rótulo acessível', async () => {
    renderizar();

    expect(await screen.findByLabelText(/e-mail/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument();
  });

  it('valida no cliente antes de chamar a API', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole('button', { name: /entrar/i }));

    expect(await screen.findByText(/informe o e-mail/i)).toBeInTheDocument();
    expect(screen.getByText(/informe a senha/i)).toBeInTheDocument();

    const chamadasDeLogin = vi
      .mocked(globalThis.fetch)
      .mock.calls.filter(([url]) => String(url).includes('/auth/login'));
    expect(chamadasDeLogin).toHaveLength(0);
  });

  it('rejeita e-mail com formato inválido', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/e-mail/i), 'nao-e-email');
    await usuario.type(screen.getByLabelText(/senha/i), 'algumaSenha123');
    await usuario.click(screen.getByRole('button', { name: /entrar/i }));

    expect(await screen.findByText(/e-mail inválido/i)).toBeInTheDocument();
  });

  it('mostra o erro do backend com o código de suporte', async () => {
    renderizar();
    const usuario = userEvent.setup();

    vi.mocked(globalThis.fetch).mockImplementation((url) => {
      if (String(url).includes('/auth/login')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              type: 'https://rfbalance/errors/invalid-credentials',
              title: 'Credenciais inválidas',
              status: 401,
              detail: 'E-mail ou senha inválidos.',
              instance: '/api/v1/auth/login',
              correlation_id: 'deadbeef1234',
              errors: [],
            }),
            { status: 401, headers: { 'Content-Type': 'application/problem+json' } },
          ),
        );
      }
      return Promise.resolve(respostaNaoAutenticado());
    });

    await usuario.type(screen.getByLabelText(/e-mail/i), 'admin@rfbalance.local');
    await usuario.type(screen.getByLabelText(/senha/i), 'senhaerrada');
    await usuario.click(screen.getByRole('button', { name: /entrar/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/e-mail ou senha inválidos/i);
    });
    expect(screen.getByText(/deadbeef/i)).toBeInTheDocument();
  });
});
