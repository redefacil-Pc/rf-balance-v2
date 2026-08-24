import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SettlementSummary, resumirFechamentos } from '@/features/settlements/components/SettlementSummary';
import type { CommissionSettlement } from '@/shared/types/commissions';

const base: CommissionSettlement = {
  id: 1,
  beneficiary_id: 1,
  beneficiary_name: 'Carla',
  roles: ['CONSULTOR'],
  period_start: '2026-08-14',
  period_end: '2026-08-20',
  gross_amount: '741.94',
  carryover_amount: '0.00',
  bonus_amount: '50.00',
  discount_amount: '20.00',
  manual_discount_amount: '20.00',
  reversal_discount_amount: '0.00',
  reversal_carryover_amount: '0.00',
  deferred_amount: '100.00',
  paid_amount: '300.00',
  payable_amount: '371.94',
  status: 'DEFERRED',
  payment_date: '2026-08-17',
  payment_method: 'PIX',
  payment_reference: 'TESTE',
  notes: null,
  created_at: '2026-08-17T12:00:00Z',
};

describe('SettlementSummary', () => {
  it('soma os valores em centavos sem usar ponto flutuante', () => {
    const summary = resumirFechamentos([
      base,
      { ...base, id: 2, gross_amount: '2800.00', bonus_amount: '0.00',
        discount_amount: '0.00', deferred_amount: '0.00', paid_amount: '2800.00',
        payable_amount: '0.00' },
    ]);
    expect(summary).toEqual({
      gross: '3541.94', additions: '50.00', deductions: '120.00',
      paid: '3100.00', payable: '371.94',
    });
  });

  it('apresenta os indicadores financeiros do período', () => {
    render(<MantineProvider><SettlementSummary items={[base]} /></MantineProvider>);
    expect(screen.getByText('Comissão bruta')).toBeInTheDocument();
    expect(screen.getByText('A pagar')).toBeInTheDocument();
    expect(screen.getByText('R$ 371,94')).toBeInTheDocument();
  });
});
