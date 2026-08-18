import { describe, expect, it } from 'vitest';

import { dataLocalHoje } from '@/shared/formatters/local-date';

describe('dataLocalHoje', () => {
  it('mantém o dia civil de São Paulo depois das 21h', () => {
    expect(dataLocalHoje(new Date('2026-08-17T23:30:00-03:00'))).toBe('2026-08-17');
  });
});
