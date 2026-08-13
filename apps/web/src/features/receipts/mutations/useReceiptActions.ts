import { useMutation, useQueryClient } from '@tanstack/react-query';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ReceiptWriteResult } from '../types';
import { receiptKeys } from '../queries/useReceipts';

export interface CreateReceiptInput {
  proposalId: number;
  amount: string;
  businessDate: string;
  paymentMethod: string;
  reference: string;
  notes: string;
  proof: File;
}

function useInvalidate() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: receiptKeys.all });
    void client.invalidateQueries({ queryKey: ['proposals'] });
  };
}

export function useCreateReceipt() {
  const invalidate = useInvalidate();
  return useMutation<ReceiptWriteResult, ApiError, CreateReceiptInput>({
    mutationFn: (input) => {
      const body = new FormData();
      body.set('amount', input.amount);
      body.set('business_date', input.businessDate);
      body.set('payment_method', input.paymentMethod);
      body.set('reference', input.reference);
      body.set('notes', input.notes);
      body.set('proof', input.proof);
      return requisitar(`/proposals/${input.proposalId}/receipts`, {
        method: 'POST', body, idempotencyKey: crypto.randomUUID(),
      });
    },
    onSuccess: invalidate,
  });
}

export function useDecideReceipt() {
  const invalidate = useInvalidate();
  return useMutation<ReceiptWriteResult, ApiError,
    { id: number; decision: 'APPROVE' | 'REJECT'; reason?: string }>({
    mutationFn: ({ id, ...body }) => requisitar(`/receipts/${id}/decision`, {
      method: 'POST', body: { decision: body.decision, reason: body.reason ?? null },
    }),
    onSuccess: invalidate,
  });
}

export function useReverseReceipt() {
  const invalidate = useInvalidate();
  return useMutation<ReceiptWriteResult, ApiError,
    { id: number; reason: string; businessDate: string }>({
    mutationFn: ({ id, reason, businessDate }) => requisitar(`/receipts/${id}/reversal`, {
      method: 'POST', body: { reason, business_date: businessDate },
    }),
    onSuccess: invalidate,
  });
}
