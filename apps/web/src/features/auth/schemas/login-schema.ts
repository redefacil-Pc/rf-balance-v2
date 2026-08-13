import { z } from 'zod';

/** Validação de forma no cliente. A regra de senha real é do backend. */
export const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Informe o e-mail')
    .email('E-mail inválido')
    .transform((valor) => valor.trim().toLowerCase()),
  password: z.string().min(1, 'Informe a senha'),
});

export type LoginForm = z.infer<typeof loginSchema>;
