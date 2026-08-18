import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PreviaDeComissao } from '@/features/proposals/components/PreviaDeComissao';
import type { CommissionPreview } from '@/features/proposals/queries/useCommissionPreview';
import type { ApiError } from '@/shared/api/problem-details';

type Resultado = Parameters<typeof PreviaDeComissao>[0]['previa'];

function resultado(data?: CommissionPreview, error?: ApiError): Resultado {
  return { data, error: error ?? null, isFetching: false } as unknown as Resultado;
}

function montar(previa: Resultado) {
  render(
    <MantineProvider>
      <QueryClientProvider client={new QueryClient()}>
        <PreviaDeComissao previa={previa} />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe('PreviaDeComissao', () => {
  it('mostra os dois valores que vieram do servidor, sem recalcular', () => {
    montar(
      resultado({
        company_commission_amount: '3000.00',
        consultant_commission_amount: '300.00',
        strategy: 'STANDARD_CONSULTANT',
        estimate: false,
        note: null,
      }),
    );

    expect(screen.getByText('R$ 3.000,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 300,00')).toBeInTheDocument();
    expect(screen.queryByText('estimativa')).not.toBeInTheDocument();
  });

  it('marca como estimativa e explica o motivo no caso escalonado', () => {
    montar(
      resultado({
        company_commission_amount: '3000.00',
        consultant_commission_amount: '450.00',
        strategy: 'SCALED_CONSULTANT',
        estimate: true,
        note: 'Estimativa: depende da produção acumulada no mês.',
      }),
    );

    expect(screen.getByText('estimativa')).toBeInTheDocument();
    expect(
      screen.getByText('Estimativa: depende da produção acumulada no mês.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Consultor escalonado — produção acumulada')).toBeInTheDocument();
  });

  it('não inventa comissão do consultor quando o servidor não soube dizer', () => {
    montar(
      resultado({
        company_commission_amount: '3000.00',
        consultant_commission_amount: null,
        strategy: null,
        estimate: false,
        note: 'Este consultor não tem função de consultor vigente nessa data.',
      }),
    );

    expect(screen.getByText('R$ 3.000,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 0,00')).toBeInTheDocument();
    expect(
      screen.getByText('Este consultor não tem função de consultor vigente nessa data.'),
    ).toBeInTheDocument();
  });
});
