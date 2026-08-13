import { describe, expect, it } from 'vitest';

import {
  decimalParaMoeda,
  mascararMoeda,
  moedaParaDecimal,
} from '@/shared/formatters/money-mask';

describe('mascararMoeda', () => {
  it('cresce da direita para a esquerda conforme se digita', () => {
    expect(mascararMoeda('1')).toBe('0,01');
    expect(mascararMoeda('14')).toBe('0,14');
    expect(mascararMoeda('146')).toBe('1,46');
    expect(mascararMoeda('1462')).toBe('14,62');
    expect(mascararMoeda('146296')).toBe('1.462,96');
    expect(mascararMoeda('1462964')).toBe('14.629,64');
  });

  it('agrupa milhares em valores grandes', () => {
    expect(mascararMoeda('123456789')).toBe('1.234.567,89');
  });

  it('ignora o que já vem formatado, sem duplicar separador', () => {
    expect(mascararMoeda('14.629,64')).toBe('14.629,64');
  });

  it('não deixa zero à esquerda se acumular', () => {
    expect(mascararMoeda('000014629')).toBe('146,29');
  });

  it('devolve vazio para entrada vazia', () => {
    expect(mascararMoeda('')).toBe('');
    expect(mascararMoeda('abc')).toBe('');
  });
});

describe('moedaParaDecimal', () => {
  it('converte o valor da tela no formato da API', () => {
    expect(moedaParaDecimal('14.629,64')).toBe('14629.64');
    expect(moedaParaDecimal('0,01')).toBe('0.01');
    expect(moedaParaDecimal('1.234.567,89')).toBe('1234567.89');
  });

  it('devolve vazio para vazio, para a validação reclamar', () => {
    expect(moedaParaDecimal('')).toBe('');
  });

  it('mantém o zero, que a validação recusa depois', () => {
    expect(moedaParaDecimal('0,00')).toBe('0.00');
  });
});

describe('decimalParaMoeda', () => {
  it('reabre o valor da API no formato da tela', () => {
    expect(decimalParaMoeda('14629.64')).toBe('14.629,64');
    expect(decimalParaMoeda('1000.00')).toBe('1.000,00');
  });

  it('sobrevive a ida e volta', () => {
    expect(moedaParaDecimal(decimalParaMoeda('99999.99'))).toBe('99999.99');
  });
});
