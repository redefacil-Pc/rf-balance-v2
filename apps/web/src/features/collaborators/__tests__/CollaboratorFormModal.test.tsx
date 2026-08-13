import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CollaboratorFormModal } from '@/features/collaborators/components/CollaboratorFormModal';

const EMPRESAS = [{ id: 1, legal_name: 'Rede Fácil LTDA', trade_name: 'Rede Fácil', is_active: true }];
const UNIDADES = [{ id: 7, company_id: 1, code: 'MATRIZ', name: 'Matriz', is_active: true }];

function responderJson(dados: unknown, status = 200): Response {
  return new Response(JSON.stringify(dados), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function renderizar() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <MantineProvider>
      <QueryClientProvider client={client}>
        <CollaboratorFormModal aberto onFechar={() => undefined} />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe('CollaboratorFormModal', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const caminho = String(url);
      if (caminho.includes('/companies')) {
        return Promise.resolve(responderJson(EMPRESAS));
      }
      if (caminho.includes('/units')) {
        return Promise.resolve(responderJson(UNIDADES));
      }
      if (caminho.includes('/users')) {
        return Promise.resolve(
          responderJson({
            items: [
              { id: 7, email: 'livre@rfbalance.local', full_name: 'Conta Livre', roles: [] },
            ],
            next_cursor: null,
          }),
        );
      }
      return Promise.resolve(responderJson({}, 404));
    });
  });

  afterEach(() => {
    vi.mocked(globalThis.fetch).mockRestore();
  });

  it('apresenta os campos obrigatórios do cadastro', async () => {
    renderizar();

    // `getAllByLabelText`: o Select do Mantine associa o rótulo a mais de um
    // elemento (o campo visível e o input oculto). O `\s*\*?` cobre o asterisco
    // que o `withAsterisk` acrescenta.
    const rotulos = [
      /^empresa\s*\*?$/i,
      /^unidade$/i,
      /^nome completo\s*\*?$/i,
      /^cpf ou cnpj\s*\*?$/i,
      /^regime\s*\*?$/i,
      /^função$/i,
      /^vigente desde$/i,
    ];

    await screen.findByLabelText(/^nome completo\s*\*?$/i);
    for (const rotulo of rotulos) {
      expect(screen.getAllByLabelText(rotulo).length).toBeGreaterThan(0);
    }
  });

  it('valida no cliente antes de chamar a API', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.click(await screen.findByRole('button', { name: /cadastrar/i }));

    expect(await screen.findByText(/selecione a empresa/i)).toBeInTheDocument();
    expect(screen.getByText(/informe o nome completo/i)).toBeInTheDocument();

    const chamadasDeCriacao = vi
      .mocked(globalThis.fetch)
      .mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'POST');
    expect(chamadasDeCriacao).toHaveLength(0);
  });

  it('rejeita documento com quantidade de dígitos inválida', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.type(await screen.findByLabelText(/nome completo/i), 'Maria Consultora');
    await usuario.type(screen.getByLabelText(/cpf ou cnpj/i), '123456');
    await usuario.click(screen.getByRole('button', { name: /cadastrar/i }));

    expect(
      await screen.findByText(/deve ter 11 dígitos \(CPF\) ou 14 \(CNPJ\)/i),
    ).toBeInTheDocument();
  });

  it('mascara o documento e escolhe o formato pelo tamanho', async () => {
    renderizar();
    const usuario = userEvent.setup();

    const campo = await screen.findByLabelText<HTMLInputElement>(/^cpf ou cnpj/i);
    await usuario.type(campo, '52998224725');
    expect(campo.value).toBe('529.982.247-25');

    await usuario.clear(campo);
    await usuario.type(campo, '11222333000181');
    expect(campo.value).toBe('11.222.333/0001-81');
  });

  it('mascara a chave PIX conforme o tipo escolhido', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.click(await screen.findByRole('textbox', { name: /^tipo$/i }));
    await usuario.click(await screen.findByRole('option', { name: 'TELEFONE' }));

    const chave = screen.getByLabelText<HTMLInputElement>(/^chave$/i);
    await usuario.type(chave, '79981031196');

    expect(chave.value).toBe('(79) 98103-1196');
  });

  it('não mascara chave de e-mail, que máscara corromperia', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.click(await screen.findByRole('textbox', { name: /^tipo$/i }));
    await usuario.click(await screen.findByRole('option', { name: 'EMAIL' }));

    const chave = screen.getByLabelText<HTMLInputElement>(/^chave$/i);
    await usuario.type(chave, 'maria@empresa.com');

    expect(chave.value).toBe('maria@empresa.com');
  });

  it('permite acumular funções, como exige o modelo de papéis', async () => {
    renderizar();
    const usuario = userEvent.setup();

    expect(await screen.findAllByLabelText(/vigente desde/i)).toHaveLength(1);

    await usuario.click(screen.getByRole('button', { name: /adicionar função/i }));

    await waitFor(async () => {
      expect(await screen.findAllByLabelText(/vigente desde/i)).toHaveLength(1);
    });
    // a segunda linha não repete o rótulo; conferimos pelo total de campos de data
    expect(document.querySelectorAll('input[type="date"]')).toHaveLength(2);
  });

  it('oferece as contas ainda sem colaborador para vínculo', async () => {
    // vincular na criação evita o cadastro em dois passos, em que uma falha no
    // segundo deixaria a pessoa sem acesso
    renderizar();

    await screen.findByLabelText(/^nome completo\s*\*?$/i);
    // `getAllByLabelText`: o Select do Mantine associa o rótulo a mais de um
    // elemento, como nos demais testes deste arquivo
    const [conta] = screen.getAllByLabelText(/^conta$/i);
    await userEvent.setup().click(conta);

    expect(await screen.findByText(/Conta Livre — livre@rfbalance.local/)).toBeInTheDocument();
  });
});
