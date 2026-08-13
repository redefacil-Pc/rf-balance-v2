import { describe, expect, it } from 'vitest';

import { rotuloDoPapel } from '@/shared/types/organization';

describe('rotuloDoPapel', () => {
  it('exibe o consultor MEI escalonado como MEI 2', () => {
    expect(rotuloDoPapel('CONSULTOR_MEI_ESCALONADO')).toBe('MEI 2');
  });

  it('formata os demais códigos sem alterar o valor usado pela API', () => {
    expect(rotuloDoPapel('LIDER_FINALIZACAO')).toBe('LIDER FINALIZACAO');
  });
});
