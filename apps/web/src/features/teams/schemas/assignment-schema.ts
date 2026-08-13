import { z } from 'zod';

import { TIPOS_DE_VINCULO } from '@/shared/types/organization';

export const assignmentSchema = z
  .object({
    consultant_id: z.number({ required_error: 'Selecione o liderado' }).int().positive(),
    leader_id: z.number({ required_error: 'Selecione o líder' }).int().positive(),
    assignment_type: z.enum(TIPOS_DE_VINCULO),
    start_date: z.string().min(1, 'Informe a data de início'),
    reason: z.string().min(3, 'Descreva o motivo — ele vai para a auditoria').max(255),
  })
  .refine((dados) => dados.consultant_id !== dados.leader_id, {
    message: 'Um colaborador não pode liderar a si mesmo',
    path: ['leader_id'],
  });

export type AssignmentForm = z.infer<typeof assignmentSchema>;
