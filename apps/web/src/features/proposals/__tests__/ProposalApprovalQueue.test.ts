import { describe, expect, it } from 'vitest';

import { proximaProposta } from '../pages/ProposalApprovalsPage';
import type { Proposal } from '@/shared/types/commercial';

function proposta(id: number): Proposal {
  return {
    id,
    external_id: null,
    business_date: '2026-08-20',
    customer_name: `Cliente ${id}`,
    customer_document: '***.***.***-**',
    consultant_id: 1,
    consultant_name: 'Consultora',
    bko_collaborator_id: null,
    finalizer_collaborator_id: null,
    operation_amount: '1000.00',
    tps_percentage: '10.000000',
    company_commission_amount: '100.00',
    paid_amount: '0.00',
    outstanding_amount: '100.00',
    status: 'OPEN',
    approval_status: 'SUBMITTED',
    version: 2,
  };
}

describe('fila de aprovação', () => {
  it('avança para a proposta seguinte após uma decisão', () => {
    expect(proximaProposta([proposta(1), proposta(2), proposta(3)], 1)?.id).toBe(2);
  });

  it('continua em outra pendência quando a última da tela foi decidida', () => {
    expect(proximaProposta([proposta(1), proposta(2), proposta(3)], 3)?.id).toBe(1);
  });

  it('fecha a análise quando não há outra pendência', () => {
    expect(proximaProposta([proposta(1)], 1)).toBeNull();
  });
});
