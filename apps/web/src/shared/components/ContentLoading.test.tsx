import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';

import { ContentLoading } from '@/shared/components/ContentLoading';

describe('ContentLoading', () => {
  it('expõe o estado de carregamento sem remover a estrutura da página', () => {
    render(
      <MantineProvider>
        <ContentLoading label="Carregando relatório" />
      </MantineProvider>,
    );

    expect(screen.getByRole('status', { name: 'Carregando relatório' })).toBeInTheDocument();
  });
});
