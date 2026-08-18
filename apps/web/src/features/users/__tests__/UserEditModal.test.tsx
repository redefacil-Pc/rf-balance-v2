import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { UserEditModal } from '@/features/users/components/UserEditModal';
import type { SystemUser } from '@/features/users/types';

const USUARIO: SystemUser = {
  id: 42,
  email: 'pessoa@rfbalance.local',
  full_name: 'Pessoa Editada',
  is_active: true,
  must_change_password: false,
  roles: ['OPERACIONAL'],
  last_login_at: null,
  collaborator_id: null,
};

function json(dados: unknown): Response {
  return new Response(JSON.stringify(dados), { headers: { 'Content-Type': 'application/json' } });
}

function renderizar() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <MantineProvider>
      <QueryClientProvider client={client}>
        <UserEditModal user={USUARIO} currentUserId={99} onClose={() => undefined} />
      </QueryClientProvider>
    </MantineProvider>,
  );
  return userEvent.setup();
}

/** Corpo enviado no POST de redefinição de senha. */
function corpoDoReset(): Record<string, unknown> | undefined {
  const chamada = vi
    .mocked(globalThis.fetch)
    .mock.calls.find(([url]) => String(url).includes('/password-reset'));
  const init = chamada?.[1] as RequestInit | undefined;
  return init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
}

describe('UserEditModal — senha', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const caminho = String(url);
      if (caminho.includes('/users/roles')) {
        return Promise.resolve(
          json([{ code: 'OPERACIONAL', name: 'Operacional', permissions: [] }]),
        );
      }
      if (caminho.includes('/password-reset')) {
        return Promise.resolve(
          json({
            id: 42,
            email: USUARIO.email,
            temporary_password: null,
            must_change_password: true,
          }),
        );
      }
      return Promise.resolve(json({ items: [], next_cursor: null }));
    });
  });

  afterEach(() => vi.mocked(globalThis.fetch).mockRestore());

  it('mantém a geração automática', async () => {
    const usuario = renderizar();

    await usuario.click(await screen.findByRole('button', { name: /^gerar$/i }));

    await waitFor(() => expect(corpoDoReset()).toBeDefined());
    // sem senha no corpo: o servidor gera
    expect(corpoDoReset()?.password).toBeNull();
  });

  it('envia a senha escolhida pelo administrador', async () => {
    const usuario = renderizar();

    await usuario.type(await screen.findByLabelText(/definir uma senha/i), 'SenhaEscolhida2026');
    await usuario.click(screen.getByRole('button', { name: /^definir$/i }));

    await waitFor(() => expect(corpoDoReset()).toBeDefined());
    expect(corpoDoReset()?.password).toBe('SenhaEscolhida2026');
    expect(corpoDoReset()?.require_change).toBe(true);
  });

  it('recusa senha curta antes de chamar a API', async () => {
    // espelha a política do backend; evita o ida-e-volta óbvio
    const usuario = renderizar();

    await usuario.type(await screen.findByLabelText(/definir uma senha/i), 'curta');

    expect(await screen.findByText(/ao menos 12 caracteres/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^definir$/i })).toBeDisabled();
    expect(corpoDoReset()).toBeUndefined();
  });

  it('permite dispensar a troca no próximo acesso', async () => {
    const usuario = renderizar();

    await usuario.type(await screen.findByLabelText(/definir uma senha/i), 'SenhaEscolhida2026');
    await usuario.click(screen.getByLabelText(/exigir troca no próximo acesso/i));
    await usuario.click(screen.getByRole('button', { name: /^definir$/i }));

    await waitFor(() => expect(corpoDoReset()).toBeDefined());
    expect(corpoDoReset()?.require_change).toBe(false);
  });

  it('não exibe de volta a senha que o administrador definiu', async () => {
    const usuario = renderizar();

    await usuario.type(await screen.findByLabelText(/definir uma senha/i), 'SenhaEscolhida2026');
    await usuario.click(screen.getByRole('button', { name: /^definir$/i }));

    expect(await screen.findByText(/^Senha definida$/i)).toBeInTheDocument();
    expect(screen.queryByText(/exibida somente agora/i)).not.toBeInTheDocument();
  });

  it('salva cadastro, perfis e situação em uma única requisição', async () => {
    const usuario = renderizar();

    await usuario.click(await screen.findByRole('button', { name: /salvar alterações/i }));

    await waitFor(() => {
      const chamadas = vi.mocked(globalThis.fetch).mock.calls.filter(([url, init]) =>
        String(url).endsWith('/users/42') && (init as RequestInit | undefined)?.method === 'PUT');
      expect(chamadas).toHaveLength(1);
      const body = JSON.parse(String((chamadas[0]?.[1] as RequestInit).body));
      expect(body).toMatchObject({ roles: ['OPERACIONAL'], is_active: true });
    });
  });
});
