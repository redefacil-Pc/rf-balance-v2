import { describe, expect, it } from 'vitest';

import {
  mascararCnpj,
  mascararCpf,
  mascararDocumento,
  temTamanhoDeDocumento,
} from '@/shared/formatters/document-mask';

describe('mascararDocumento', () => {
  it('formata CPF completo', () => {
    expect(mascararDocumento('52998224725')).toBe('529.982.247-25');
  });

  it('formata CNPJ completo', () => {
    expect(mascararDocumento('11222333000181')).toBe('11.222.333/0001-81');
  });

  it('formata parcialmente enquanto o operador digita', () => {
    expect(mascararDocumento('529')).toBe('529');
    expect(mascararDocumento('5299')).toBe('529.9');
    expect(mascararDocumento('529982')).toBe('529.982');
    expect(mascararDocumento('5299822')).toBe('529.982.2');
    expect(mascararDocumento('529982247')).toBe('529.982.247');
    expect(mascararDocumento('5299822472')).toBe('529.982.247-2');
  });

  it('troca para o formato de CNPJ ao passar de 11 dígitos', () => {
    expect(mascararDocumento('112223330001')).toBe('11.222.333/0001');
  });

  it('descarta o que passa de 14 dígitos', () => {
    expect(mascararDocumento('11222333000181999')).toBe('11.222.333/0001-81');
  });

  it('ignora o que já vem formatado, sem duplicar separador', () => {
    expect(mascararDocumento('529.982.247-25')).toBe('529.982.247-25');
  });

  it('descarta letras coladas', () => {
    expect(mascararDocumento('529abc982')).toBe('529.982');
  });

  it('devolve vazio para entrada vazia', () => {
    expect(mascararDocumento('')).toBe('');
  });
});

describe('mascararCpf e mascararCnpj', () => {
  it('respeitam o próprio limite de dígitos', () => {
    expect(mascararCpf('52998224725999')).toBe('529.982.247-25');
    expect(mascararCnpj('11222333000181999')).toBe('11.222.333/0001-81');
  });
});

describe('temTamanhoDeDocumento', () => {
  it('aceita 11 e 14 dígitos, com ou sem máscara', () => {
    expect(temTamanhoDeDocumento('529.982.247-25')).toBe(true);
    expect(temTamanhoDeDocumento('11222333000181')).toBe(true);
  });

  it('recusa qualquer outro tamanho', () => {
    expect(temTamanhoDeDocumento('529982')).toBe(false);
    expect(temTamanhoDeDocumento('')).toBe(false);
    expect(temTamanhoDeDocumento('529982247251')).toBe(false);
  });
});
