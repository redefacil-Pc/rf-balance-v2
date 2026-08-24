import { describe, expect, it } from 'vitest';

import { formatarDataHora, formatarPercentual, somarValores } from './proposal-approval-formatters';

describe('formatadores da aprovação', () => {
  it('soma dinheiro sem erro de ponto flutuante', () => {
    expect(somarValores(['0.10', '0.20', '1234.56'])).toBe('1234.86');
  });

  it('normaliza casas decimais para a apresentação', () => {
    expect(somarValores(['10', '1.5'])).toBe('11.50');
    expect(formatarPercentual('35.500000')).toBe('35,5%');
  });

  it('explicita quando o horário não existe', () => {
    expect(formatarDataHora(null)).toBe('Horário não informado');
  });
});
