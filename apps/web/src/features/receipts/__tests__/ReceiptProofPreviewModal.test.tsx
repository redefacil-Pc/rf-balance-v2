import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ReceiptProofPreviewModal } from '../components/ReceiptProofPreviewModal';

describe('ReceiptProofPreviewModal', () => {
  it('exibe o comprovante inline e mantém o download disponível', () => {
    render(
      <MantineProvider>
        <ReceiptProofPreviewModal
          receipt={{ id: 42, proof_file_name: 'comprovante.pdf' }}
          onClose={vi.fn()}
        />
      </MantineProvider>,
    );

    expect(screen.getByTitle('Pré-visualização de comprovante.pdf')).toHaveAttribute(
      'src',
      '/api/v1/receipts/42/proof?preview=true',
    );
    expect(screen.getByRole('link', { name: 'Baixar' })).toHaveAttribute(
      'href',
      '/api/v1/receipts/42/proof',
    );
    expect(screen.getByRole('link', { name: 'Abrir em nova aba' })).toHaveAttribute(
      'href',
      '/api/v1/receipts/42/proof?preview=true',
    );
  });
});
