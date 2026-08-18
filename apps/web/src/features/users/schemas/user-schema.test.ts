import { describe, expect, it } from 'vitest';

import { userSchema } from '@/features/users/schemas/user-schema';

const base = {
  full_name: 'Diego Consultor',
  email: 'diego@example.com',
  roles: ['CONSULTOR'] as const,
  is_collaborator: true,
  company_id: 1,
  unit_id: null,
  document: '529.982.247-25',
  function: 'CONSULTOR_MEI_ESCALONADO' as const,
  valid_from: '2026-08-17',
};

describe('userSchema', () => {
  it('aceita MEI 2 como função de consultor com regime tributário MEI', () => {
    expect(userSchema.safeParse({ ...base, tax_regime: 'MEI' }).success).toBe(true);
  });

  it('aceita função escalonada com regime CLT', () => {
    const result = userSchema.safeParse({ ...base, tax_regime: 'CLT' });
    expect(result.success).toBe(true);
  });
});
