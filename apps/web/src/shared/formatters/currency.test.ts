import { describe, expect, it } from 'vitest';

import { formatarMoeda, formatarMoedaOuVazio } from '@/shared/formatters/currency';

// Intl.NumberFormat separa o símbolo do valor com espaço não-quebrável (U+00A0),
// não com espaço comum. As expectativas usam o caractere real.
const NBSP = ' ';

describe('formatarMoeda', () => {
  it('formata string decimal em real', () => {
    expect(formatarMoeda('1234.56')).toBe(`R$${NBSP}1.234,56`);
  });

  it('preserva duas casas quando vem sem decimais', () => {
    expect(formatarMoeda('1000')).toBe(`R$${NBSP}1.000,00`);
  });

  it('formata valor negativo', () => {
    expect(formatarMoeda('-250.10')).toBe(`-R$${NBSP}250,10`);
  });

  it('aceita escala adicional quando contém somente zeros', () => {
    expect(formatarMoeda('-5000.000')).toBe(`-R$${NBSP}5.000,00`);
  });

  it('rejeita valor com mais de duas casas', () => {
    expect(() => formatarMoeda('10.005')).toThrow();
  });

  it('rejeita número em ponto flutuante disfarçado', () => {
    expect(() => formatarMoeda('1e3')).toThrow();
  });

  it('mostra travessão para ausência de valor', () => {
    expect(formatarMoedaOuVazio(null)).toBe('—');
  });
});
