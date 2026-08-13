import { describe, expect, it } from 'vitest';

import { mascararTelefone } from '@/shared/formatters/phone-mask';
import { mascararChavePix } from '@/shared/formatters/pix-mask';

describe('mascararTelefone', () => {
  it('formata celular com nono dígito', () => {
    expect(mascararTelefone('79981031196')).toBe('(79) 98103-1196');
  });

  it('formata fixo de oito dígitos', () => {
    expect(mascararTelefone('7932114455')).toBe('(79) 3211-4455');
  });

  it('formata parcialmente enquanto se digita', () => {
    expect(mascararTelefone('79')).toBe('79');
    expect(mascararTelefone('7998')).toBe('(79) 98');
  });
});

describe('mascararChavePix', () => {
  it('mascara as chaves de formato conhecido', () => {
    expect(mascararChavePix('CPF')('52998224725')).toBe('529.982.247-25');
    expect(mascararChavePix('CNPJ')('11222333000181')).toBe('11.222.333/0001-81');
    expect(mascararChavePix('TELEFONE')('79981031196')).toBe('(79) 98103-1196');
  });

  it('não toca em e-mail nem em chave aleatória', () => {
    // mascarar aqui corromperia a chave usada para pagar alguém
    expect(mascararChavePix('EMAIL')('maria@empresa.com')).toBe('maria@empresa.com');
    const aleatoria = '123e4567-e89b-12d3-a456-426614174000';
    expect(mascararChavePix('ALEATORIA')(aleatoria)).toBe(aleatoria);
  });

  it('sem tipo escolhido, não altera o que foi digitado', () => {
    expect(mascararChavePix(undefined)('52998224725')).toBe('52998224725');
  });
});
