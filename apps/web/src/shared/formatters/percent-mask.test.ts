import { describe, expect, it } from 'vitest';

import {
  decimalParaPercentual,
  mascararPercentual,
  percentualParaDecimal,
} from '@/shared/formatters/percent-mask';

describe('mascararPercentual', () => {
  it('deixa digitar naturalmente, em unidades', () => {
    expect(mascararPercentual('12')).toBe('12');
    expect(mascararPercentual('12,5')).toBe('12,5');
    expect(mascararPercentual('30')).toBe('30');
  });

  it('aceita ponto e normaliza para vírgula', () => {
    expect(mascararPercentual('12.5')).toBe('12,5');
  });

  it('não deixa mais de uma vírgula virar separador', () => {
    expect(mascararPercentual('12,5,7')).toBe('12,57');
  });

  it('limita a seis casas decimais, como a coluna', () => {
    expect(mascararPercentual('3,3333339')).toBe('3,333333');
  });

  it('descarta letras', () => {
    expect(mascararPercentual('12a,5b')).toBe('12,5');
  });

  it('não impede digitar acima de 100 — quem recusa é a validação, com mensagem', () => {
    expect(mascararPercentual('101')).toBe('101');
  });

  it('preserva a vírgula recém-digitada', () => {
    expect(mascararPercentual('12,')).toBe('12,');
  });
});

describe('percentualParaDecimal', () => {
  it('converte o valor da tela no formato da API', () => {
    expect(percentualParaDecimal('12,5')).toBe('12.5');
    expect(percentualParaDecimal('30')).toBe('30');
  });

  it('devolve vazio para vazio', () => {
    expect(percentualParaDecimal('')).toBe('');
  });
});

describe('decimalParaPercentual', () => {
  it('reabre sem zeros inúteis', () => {
    expect(decimalParaPercentual('30.000000')).toBe('30');
    expect(decimalParaPercentual('12.500000')).toBe('12,5');
    expect(decimalParaPercentual('3.333333')).toBe('3,333333');
  });

  it('sobrevive a ida e volta', () => {
    expect(percentualParaDecimal(decimalParaPercentual('12.500000'))).toBe('12.5');
  });
});
