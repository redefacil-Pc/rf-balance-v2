import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ProposalFormModal } from '@/features/proposals/components/ProposalFormModal';

const COLABORADORES = {
  items: [
    {
      id: 3,
      full_name: 'Maria Consultora',
      company_id: 1,
      unit_id: null,
      tax_regime: 'MEI',
      is_active: true,
      roles: ['CONSULTOR'],
      document: '***.***.247-25',
      document_type: 'CPF',
    },
  ],
  next_cursor: null,
};

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
        <ProposalFormModal aberto onFechar={() => undefined} />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

function chamadasDePost() {
  return vi
    .mocked(globalThis.fetch)
    .mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'POST');
}

describe('ProposalFormModal', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (String(url).includes('/collaborators')) {
        return Promise.resolve(responderJson(COLABORADORES));
      }
      return Promise.resolve(responderJson({}, 404));
    });
  });

  afterEach(() => {
    vi.mocked(globalThis.fetch).mockRestore();
  });

  it('apresenta os campos canônicos da proposta', async () => {
    renderizar();

    await screen.findByLabelText(/^cliente\s*\*?$/i);
    const rotulos = [
      /^consultor\s*\*?$/i,
      /^data de negócio\s*\*?$/i,
      /^cliente\s*\*?$/i,
      /^cpf ou cnpj do cliente\s*\*?$/i,
      /^valor da operação\s*\*?$/i,
      /^tps \(%\)\s*\*?$/i,
      /^redmine$/i,
    ];
    for (const rotulo of rotulos) {
      expect(screen.getAllByLabelText(rotulo).length).toBeGreaterThan(0);
    }
  });

  it('valida no cliente antes de chamar a API', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.click(await screen.findByRole('button', { name: /cadastrar/i }));

    expect(await screen.findByText(/selecione o consultor/i)).toBeInTheDocument();
    expect(screen.getByText(/informe o nome do cliente/i)).toBeInTheDocument();
    expect(screen.getByText(/informe o valor da operação/i)).toBeInTheDocument();
    expect(chamadasDePost()).toHaveLength(0);
  });

  it('recusa valor de operação zerado', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.type(await screen.findByLabelText(/^valor da operação/i), '0');
    await usuario.click(screen.getByRole('button', { name: /cadastrar/i }));

    expect(await screen.findByText(/maior que zero/i)).toBeInTheDocument();
    expect(chamadasDePost()).toHaveLength(0);
  });

  it('recusa TPS acima de 100', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.type(await screen.findByLabelText(/^tps \(%\)/i), '101');
    await usuario.click(screen.getByRole('button', { name: /cadastrar/i }));

    expect(await screen.findByText(/vai de 0 a 100/i)).toBeInTheDocument();
    expect(chamadasDePost()).toHaveLength(0);
  });

  it('deixa claro que o cálculo da comissão é do servidor', async () => {
    renderizar();
    expect(await screen.findByText(/calculada no servidor/i)).toBeInTheDocument();
  });

  it('mascara o valor da operação enquanto se digita', async () => {
    renderizar();
    const usuario = userEvent.setup();

    const campo = await screen.findByLabelText<HTMLInputElement>(/^valor da operação/i);
    await usuario.type(campo, '1462964');

    // o operador digita só dígitos e o valor cresce da direita para a esquerda
    expect(campo.value).toBe('14.629,64');
  });

  it('mascara o documento do cliente e escolhe o formato pelo tamanho', async () => {
    renderizar();
    const usuario = userEvent.setup();

    const campo = await screen.findByLabelText<HTMLInputElement>(/^cpf ou cnpj do cliente/i);
    await usuario.type(campo, '52998224725');
    expect(campo.value).toBe('529.982.247-25');

    await usuario.clear(campo);
    await usuario.type(campo, '11222333000181');
    expect(campo.value).toBe('11.222.333/0001-81');
  });

  it('deixa o TPS ser digitado com vírgula', async () => {
    renderizar();
    const usuario = userEvent.setup();

    const campo = await screen.findByLabelText<HTMLInputElement>(/^tps \(%\)/i);
    await usuario.type(campo, '12,5');

    expect(campo.value).toBe('12,5');
  });

  it('envia dinheiro e documento no formato do contrato, sem máscara', async () => {
    renderizar();
    const usuario = userEvent.setup();

    await usuario.type(await screen.findByLabelText(/^cliente/i), 'Cliente Exemplo');
    await usuario.type(screen.getByLabelText(/^cpf ou cnpj do cliente/i), '52998224725');
    await usuario.type(screen.getByLabelText(/^valor da operação/i), '1462964');
    await usuario.type(screen.getByLabelText(/^tps \(%\)/i), '12,5');

    // o consultor é um Select: preenchemos pelo input oculto do Mantine
    const consultor = screen.getByRole('textbox', { name: /^consultor/i });
    await usuario.click(consultor);
    await usuario.click(await screen.findByRole('option', { name: /maria consultora/i }));

    await usuario.click(screen.getByRole('button', { name: /cadastrar/i }));

    await waitFor(() => expect(chamadasDePost()).toHaveLength(1));
    const init = chamadasDePost()[0]?.[1] as RequestInit;
    const corpo = JSON.parse(String(init.body)) as Record<string, unknown>;

    expect(corpo.operation_amount).toBe('14629.64');
    expect(corpo.tps_percentage).toBe('12.5');
    expect(corpo.customer_document).toBe('52998224725');
  });
});
