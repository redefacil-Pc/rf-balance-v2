import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ReceiptCreateModal } from '@/features/proposals/components/ReceiptCreateModal';

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
        <ReceiptCreateModal opened proposalId={7} onClose={() => undefined} />
      </QueryClientProvider>
    </MantineProvider>,
  );
  return userEvent.setup();
}

describe('ReceiptCreateModal — valor', () => {
  afterEach(() => vi.restoreAllMocks());

  it('mascara o valor digitado e envia a string decimal da API', async () => {
    let body: FormData | undefined;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      if (String(url).includes('/receipts') && init?.method === 'POST') {
        body = init.body as FormData;
        return Promise.resolve(json({ id: 1 }, 201));
      }
      return Promise.resolve(json({}, 404));
    });
    const user = montar();

    // as mesmas teclas que em "Valor da operação" da proposta: sem máscara isto
    // viraria R$ 150.000,00 — cem vezes o valor pretendido
    const valor = screen.getByRole('textbox', { name: /Valor recebido/ });
    await user.type(valor, '150000');
    expect(valor).toHaveValue('1.500,00');

    const arquivo = new File([new Uint8Array([1, 2, 3])], 'comprovante.pdf', {
      type: 'application/pdf',
    });
    // o FileButton do Mantine mantém o input escondido, sem label associada
    const entradaDeArquivo = document.querySelector<HTMLInputElement>('input[type="file"]');
    await user.upload(entradaDeArquivo as HTMLInputElement, arquivo);
    await user.click(screen.getByRole('button', { name: 'Declarar recebimento' }));

    await waitFor(() => expect(body?.get('amount')).toBe('1500.00'));
  });

  it('não deixa declarar valor zerado, que a API recusaria', async () => {
    const user = montar();

    await user.type(screen.getByRole('textbox', { name: /Valor recebido/ }), '000');
    expect(screen.getByRole('textbox', { name: /Valor recebido/ })).toHaveValue('0,00');
    expect(screen.getByRole('button', { name: 'Declarar recebimento' })).toBeDisabled();
  });
});
