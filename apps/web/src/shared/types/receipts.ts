export type ReceiptStatus = 'SUBMITTED' | 'APPROVED' | 'REJECTED';

export interface Receipt {
  id: number;
  proposal_id: number;
  proposal_approval_status: string;
  customer_name: string;
  amount: string;
  business_date: string;
  payment_datetime: string | null;
  payment_method: string;
  receiving_account_id: number | null;
  receiving_account_label: string | null;
  reference: string | null;
  notes: string | null;
  status: ReceiptStatus;
  rejection_reason: string | null;
  proof_file_name: string;
  created_at: string;
  created_by: number;
  creator_name: string;
  decided_at: string | null;
  decided_by: number | null;
  reversed: boolean;
  reversed_amount: string;
  net_amount: string;
  reversal_reason: string | null;
}

export interface ReceiptPage { items: Receipt[] }

export interface ReceiptWriteResult {
  id: number;
  proposal_id: number;
  status: ReceiptStatus;
  amount: string;
  proposal_status: string;
  proposal_paid_amount: string;
  proposal_outstanding_amount: string;
}

export interface CommissionEntry {
  id: number;
  entry_type: 'CREDIT' | 'DEBIT';
  amount: string;
  competence_date: string;
  description: string;
  reversal_id: number | null;
  created_at: string;
}

export interface CommissionCalculation {
  id: number;
  proposal_id: number;
  receipt_id: number;
  beneficiary_id: number;
  beneficiary_name: string;
  strategy: string;
  rule_version: string | null;
  competence_date: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  calculated_at: string;
  entries: CommissionEntry[];
  net_amount: string;
}

export interface CommissionExplanation {
  items: CommissionCalculation[];
  total_net_amount: string;
}
