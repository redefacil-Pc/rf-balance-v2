import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  obterDataHoraEmSaoPaulo,
} from '@/features/proposals/components/PagamentoNoCadastro';
import { ProposalFormModal } from '@/features/proposals/components/ProposalFormModal';

const COLABORADORES = {
  items: [{ id: 1, full_name: 'Maria Consultora' }],
  next_cursor: null,
};

const CONTAS = [
  {
    id: 7,
    label: 'Almeida Serviços LTDA (SANTANDER)',
    display_order: 1,
    is_active: true,
    created_at: '2026-08-18T12:00:00Z',
    updated_at: '2026-08-18T12:00:00Z',
  },
];

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function montar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <MantineProvider>
      <QueryClientProvider client={client}>
        <ProposalFormModal aberto podeDeclararPagamento onFechar={() => undefined} />
      </QueryClientProvider>
    </MantineProvider>,
  );
  return userEvent.setup();
}

function CenarioReabertura() {
  const [aberto, setAberto] = useState(true);
  return (
    <>
      {!aberto && <button onClick={() => setAberto(true)}>Reabrir cadastro</button>}
      <ProposalFormModal
        aberto={aberto}
        podeDeclararPagamento
        onFechar={() => setAberto(false)}
      />
    </>
  );
}

function montarCenarioReabertura() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <MantineProvider>
      <QueryClientProvider client={client}>
        <CenarioReabertura />
      </QueryClientProvider>
    </MantineProvider>,
  );
  return userEvent.setup();
}

async function preencherProposta(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText(/^cliente/i), 'Cliente Exemplo');
  await user.type(screen.getByLabelText(/^cpf ou cnpj do cliente/i), '52998224725');
  await user.type(screen.getByLabelText(/^valor da operação/i), '1000000');
  await user.type(screen.getByLabelText(/^tps \(%\)/i), '10');
  await user.click(screen.getByRole('textbox', { name: /^consultor/i }));
  await user.click(await screen.findByRole('option', { name: /maria consultora/i }));
}

describe('Pagamento no cadastro da proposta', () => {
  afterEach(() => vi.restoreAllMocks());

  function mockarApi(aoCriarRecebimento?: (body: FormData) => void) {
    return vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      const caminho = String(url);
      if (caminho.includes('/collaborators')) return Promise.resolve(json(COLABORADORES));
      if (caminho.includes('/receiving-accounts')) return Promise.resolve(json(CONTAS));
      if (caminho.includes('/commission-preview')) {
        return Promise.resolve(
          json({
            company_commission_amount: '1000.00',
            consultant_commission_amount: '60.00',
            strategy: 'STANDARD_CONSULTANT',
            estimate: false,
            note: null,
          }),
        );
      }
      if (caminho.includes('/proposals/with-receipt') && init?.method === 'POST') {
        aoCriarRecebimento?.(init.body as FormData);
        return Promise.resolve(
          json(
            {
              id: 3,
              receipt_id: 5,
              version: 1,
              status: 'OPEN',
              company_commission_amount: '1000.00',
              outstanding_amount: '1000.00',
            },
            201,
          ),
        );
      }
      if (caminho.includes('/proposals') && init?.method === 'POST') {
        return Promise.resolve(json({ id: 3, version: 1, company_commission_amount: '1000.00' }, 201));
      }
      return Promise.resolve(json({}, 404));
    });
  }

  it('cadastra a proposta em aberto quando o valor pago fica em branco', async () => {
    let declarou = false;
    mockarApi(() => {
      declarou = true;
    });
    const user = montar();

    await preencherProposta(user);
    await user.click(screen.getByRole('button', { name: 'Cadastrar' }));

    await waitFor(() =>
      expect(
        vi.mocked(globalThis.fetch).mock.calls.some(
          ([url, init]) =>
            String(url).includes('/proposals') && (init as RequestInit | undefined)?.method === 'POST',
        ),
      ).toBe(true),
    );
    // sem valor pago não há recebimento: a proposta nasce aberta
    expect(declarou).toBe(false);
  });

  it('trava o cadastro quando o valor foi informado sem comprovante', async () => {
    mockarApi();
    const user = montar();

    await preencherProposta(user);
    await user.type(screen.getByLabelText(/^valor pago/i), '100000');

    expect(screen.getByRole('button', { name: 'Cadastrar' })).toBeDisabled();
    expect(
      screen.getByText(/Informe forma de pagamento, conta que recebeu e comprovante/i),
    ).toBeInTheDocument();
  });

  it('cadastra proposta e recebimento na mesma requisição quando o bloco está completo', async () => {
    let corpo: FormData | undefined;
    mockarApi((body) => {
      corpo = body;
    });
    const user = montar();

    await preencherProposta(user);
    await user.type(screen.getByLabelText(/^valor pago/i), '100000');

    await user.click(screen.getByRole('textbox', { name: /conta que recebeu/i }));
    await user.click(await screen.findByRole('option', { name: /almeida serviços/i }));

    const arquivo = new File([new Uint8Array([1, 2, 3])], 'comprovante.pdf', {
      type: 'application/pdf',
    });
    const entradas = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
    await user.upload(entradas[0] as HTMLInputElement, arquivo);

    await user.click(screen.getByRole('button', { name: 'Cadastrar' }));

    await waitFor(() => expect(corpo?.get('amount')).toBe('1000.00'));
    expect(corpo?.get('customer_name')).toBe('Cliente Exemplo');
    expect(corpo?.get('operation_amount')).toBe('10000.00');
    expect(corpo?.get('receiving_account_id')).toBe('7');
    expect(corpo?.get('payment_method')).toBe('PIX');
    expect(corpo?.get('proof')).toBeInstanceOf(File);
    expect(
      vi.mocked(globalThis.fetch).mock.calls.filter(
        ([url, init]) => String(url).includes('/proposals') && init?.method === 'POST',
      ),
    ).toHaveLength(1);
  });

  it('descarta proposta, pagamento e comprovante ao cancelar e reabrir', async () => {
    mockarApi();
    const user = montarCenarioReabertura();

    await user.type(await screen.findByLabelText(/^cliente/i), 'Cliente que foi cancelado');
    await user.type(screen.getByLabelText(/^valor pago/i), '100000');
    await user.click(screen.getByRole('textbox', { name: /conta que recebeu/i }));
    await user.click(await screen.findByRole('option', { name: /almeida serviços/i }));
    const arquivo = new File([new Uint8Array([1, 2, 3])], 'comprovante-antigo.pdf', {
      type: 'application/pdf',
    });
    await user.upload(
      document.querySelector<HTMLInputElement>('input[type="file"]') as HTMLInputElement,
      arquivo,
    );
    expect(screen.getByRole('button', { name: 'comprovante-antigo.pdf' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Cancelar' }));
    await user.click(await screen.findByRole('button', { name: 'Reabrir cadastro' }));

    expect(await screen.findByLabelText(/^cliente/i)).toHaveValue('');
    expect(screen.getByLabelText(/^valor pago/i)).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Selecionar PDF, JPG ou PNG' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /conta que recebeu/i })).toHaveValue('');
  });

  it('calcula a data e a hora no fuso de São Paulo', () => {
    expect(obterDataHoraEmSaoPaulo(new Date('2026-08-21T02:30:00.000Z'))).toEqual({
      data: '2026-08-20',
      hora: '23:30',
    });
  });
});
