import { describe, expect, it } from 'vitest';

import { collaboratorSchema } from '@/features/collaborators/schemas/collaborator-schema';

describe('collaboratorSchema — modalidades', () => {
  it('não permite cadastrar consultor padrão e escalonado ao mesmo tempo', () => {
    const resultado = collaboratorSchema.safeParse({
      company_id: 1,
      unit_id: null,
      full_name: 'Consultora duplicada',
      document: '529.982.247-25',
      tax_regime: 'MEI',
      roles: [
        { role: 'CONSULTOR', valid_from: '2026-08-17' },
        { role: 'CONSULTOR_MEI_ESCALONADO', valid_from: '2026-08-17' },
      ],
      user_id: null,
    });

    expect(resultado.success).toBe(false);
    expect(
      resultado.error?.issues.some((item) => item.message.includes('apenas uma modalidade')),
    ).toBe(true);
  });
});
