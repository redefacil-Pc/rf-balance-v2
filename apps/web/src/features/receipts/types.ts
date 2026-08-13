export type ReceiptStatus = 'SUBMITTED' | 'APPROVED' | 'REJECTED';

export interface Receipt {
  id: number;
  proposal_id: number;
  customer_name: string;
  amount: string;
  business_date: string;
  payment_method: string;
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
