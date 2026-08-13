/**
 * Tipos do módulo comercial, espelhando os DTOs do backend em `snake_case`
 * (ADR-0015). Provisórios: serão substituídos pelos gerados do OpenAPI.
 *
 * Todo valor monetário chega como **string decimal** ("1234.56") e assim
 * permanece até a formatação. O frontend nunca calcula dinheiro.
 */

export const STATUS_DA_PROPOSTA = ['OPEN', 'PARTIALLY_PAID', 'PAID', 'CANCELLED'] as const;

export type StatusDaProposta = (typeof STATUS_DA_PROPOSTA)[number];

export const ROTULO_DO_STATUS: Record<StatusDaProposta, string> = {
  OPEN: 'Em aberto',
  PARTIALLY_PAID: 'Parcialmente paga',
  PAID: 'Quitada',
  CANCELLED: 'Cancelada',
};

export const COR_DO_STATUS: Record<StatusDaProposta, string> = {
  OPEN: 'blue',
  PARTIALLY_PAID: 'yellow',
  PAID: 'positivo',
  CANCELLED: 'gray',
};

export const SITUACAO_DE_APROVACAO = ['DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED'] as const;

export type SituacaoDeAprovacao = (typeof SITUACAO_DE_APROVACAO)[number];

export const ROTULO_DA_APROVACAO: Record<SituacaoDeAprovacao, string> = {
  DRAFT: 'Rascunho',
  SUBMITTED: 'Aguardando financeiro',
  APPROVED: 'Aprovada',
  REJECTED: 'Devolvida',
};

export const COR_DA_APROVACAO: Record<SituacaoDeAprovacao, string> = {
  DRAFT: 'gray',
  SUBMITTED: 'yellow',
  APPROVED: 'positivo',
  REJECTED: 'red',
};

export interface Proposal {
  id: number;
  external_id: string | null;
  business_date: string;
  customer_name: string;
  /** Mascarado quando o usuário não tem `proposals:read_pii`. */
  customer_document: string;
  consultant_id: number;
  consultant_name: string;
  bko_collaborator_id: number | null;
  finalizer_collaborator_id: number | null;
  operation_amount: string;
  tps_percentage: string;
  company_commission_amount: string;
  paid_amount: string;
  outstanding_amount: string;
  status: StatusDaProposta;
  approval_status: SituacaoDeAprovacao;
  version: number;
}

export interface ProposalDetail extends Proposal {
  bko_collaborator_name: string | null;
  finalizer_collaborator_name: string | null;
  /** Recebido acima do excedente tolerado — exige decisão do financeiro. */
  overpaid: boolean;
  tolerance_policy_version: string;
  rejection_reason: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  settled_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
}

export interface ProposalPage {
  items: Proposal[];
  next_cursor: string | null;
}

/** Retorno das escritas: só o que mudou, já calculado pelo servidor. */
export interface ProposalWriteResult {
  id: number;
  status: StatusDaProposta;
  company_commission_amount: string;
  outstanding_amount: string;
  version: number;
}

export interface ProposalCancelResult {
  id: number;
  status: StatusDaProposta;
  version: number;
}

export interface SubmitProposalResult {
  id: number;
  approval_status: SituacaoDeAprovacao;
  version: number;
}

export interface DecisionResult {
  id: number;
  approval_status: SituacaoDeAprovacao;
  rejection_reason: string | null;
  version: number;
}

/** Comprovante de pagamento anexado à proposta. */
export interface ProposalAttachment {
  id: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  uploaded_at: string;
  uploaded_by: number | null;
}
