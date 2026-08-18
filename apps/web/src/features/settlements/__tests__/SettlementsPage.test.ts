import { describe, expect, it } from 'vitest';

import { classificarSetorFechamento } from '@/features/settlements/pages/SettlementsPage';
import type { CommissionSettlement } from '@/shared/types/commissions';

function settlement(roles: string[]): CommissionSettlement {
  return { roles } as CommissionSettlement;
}

describe('classificarSetorFechamento', () => {
  it('separa consultores, finalização, BKO e reúne todas as lideranças', () => {
    expect(classificarSetorFechamento(settlement(['CONSULTOR']))).toBe('CONSULTANTS');
    expect(classificarSetorFechamento(settlement(['CONSULTOR_MEI_ESCALONADO']))).toBe('CONSULTANTS');
    expect(classificarSetorFechamento(settlement(['FINALIZACAO']))).toBe('FINALIZATION');
    expect(classificarSetorFechamento(settlement(['BKO']))).toBe('BKO');
    expect(classificarSetorFechamento(settlement(['LIDER']))).toBe('LEADERS');
    expect(classificarSetorFechamento(settlement(['LIDER_MEI_GERAL']))).toBe('LEADERS');
    expect(classificarSetorFechamento(settlement(['LIDER_FINALIZACAO']))).toBe('LEADERS');
  });

  it('prioriza liderança quando o colaborador acumulou funções no período', () => {
    expect(classificarSetorFechamento(settlement(['CONSULTOR', 'LIDER']))).toBe('LEADERS');
  });
});
