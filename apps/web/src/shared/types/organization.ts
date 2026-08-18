/**
 * Tipos da organização, espelhando os DTOs do backend em `snake_case`
 * (ADR-0015). Provisórios: serão substituídos pelos gerados do OpenAPI.
 */

export type TaxRegime = 'MEI' | 'CLT';

export const PAPEIS = [
  'CONSULTOR',
  'CONSULTOR_MEI_ESCALONADO',
  'LIDER',
  'LIDER_MEI_GERAL',
  'BKO',
  'FINALIZACAO',
  'LIDER_FINALIZACAO',
] as const;

export type Papel = (typeof PAPEIS)[number];

const ROTULOS_DOS_PAPEIS: Record<string, string> = {
  CONSULTOR: 'Consultor padrão',
  CONSULTOR_MEI_ESCALONADO: 'Consultor escalonado',
};

/** Mantém o código canônico na API e aplica apenas o nome amigável no front. */
export function rotuloDoPapel(papel: string): string {
  return ROTULOS_DOS_PAPEIS[papel] ?? papel.replaceAll('_', ' ');
}

/**
 * Função operacional com vigência (ADR-0013). Trocar de função encerra uma
 * linha e abre outra — por isso o histórico vem junto das vigentes.
 */
export interface CollaboratorFunction {
  id: number;
  role: Papel;
  valid_from: string;
  valid_to: string | null;
  current: boolean;
}

export const TIPOS_DE_VINCULO = ['COMERCIAL', 'MEI_GERAL', 'FINALIZACAO'] as const;

export type TipoDeVinculo = (typeof TIPOS_DE_VINCULO)[number];

export interface Company {
  id: number;
  legal_name: string;
  trade_name: string;
  is_active: boolean;
}

export interface Unit {
  id: number;
  company_id: number;
  code: string;
  name: string;
  is_active: boolean;
}

export interface Collaborator {
  id: number;
  full_name: string;
  company_id: number;
  unit_id: number | null;
  tax_regime: string;
  is_active: boolean;
  roles: string[];
  /** Mascarado quando o usuário não tem `collaborators:read_pii`. */
  document: string;
  document_type: string;
  /** Conta de acesso vinculada; nulo para quem não usa o sistema. */
  user_id: number | null;
  user_full_name?: string | null;
  user_email?: string | null;
  user_is_active?: boolean | null;
}

export interface CollaboratorPage {
  items: Collaborator[];
  next_cursor: string | null;
}

export interface CollaboratorDetail {
  id: number;
  email: string | null;
  phone: string | null;
  user_id: number | null;
  payment_key_type: string | null;
  payment_key_masked: string | null;
}

export interface Assignment {
  id: number;
  consultant_id: number;
  leader_id: number;
  assignment_type: string;
  start_date: string;
  end_date: string | null;
  previous_closed_on?: string | null;
}

export interface ActiveTeamAssignment {
  id: number;
  member_id: number;
  member_name: string;
  leader_id: number;
  leader_name: string;
  assignment_type: TipoDeVinculo;
  start_date: string;
  end_date: string | null;
}
