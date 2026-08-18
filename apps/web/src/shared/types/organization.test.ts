import { describe, expect, it } from 'vitest';

import { rotuloDoPapel } from '@/shared/types/organization';

describe('rotuloDoPapel', () => {
  it('exibe o nome operacional do consultor escalonado', () => {
    expect(rotuloDoPapel('CONSULTOR_MEI_ESCALONADO')).toBe('Consultor escalonado');
  });

  it('formata os demais códigos sem alterar o valor usado pela API', () => {
    expect(rotuloDoPapel('LIDER_FINALIZACAO')).toBe('LIDER FINALIZACAO');
  });
});
