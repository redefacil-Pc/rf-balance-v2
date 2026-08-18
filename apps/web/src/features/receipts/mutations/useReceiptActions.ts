import { useMutation, useQueryClient } from '@tanstack/react-query';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ReceiptWriteResult } from '@/shared/types/receipts';
import { receiptKeys } from '../queries/useReceipts';

function useInvalidate() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: receiptKeys.all });
    void client.invalidateQueries({ queryKey: ['proposals'] });
  };
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
    { id: number; reason: string; businessDate: string; amount: string }>({
    mutationFn: ({ id, reason, businessDate, amount }) => requisitar(`/receipts/${id}/reversal`, {
      method: 'POST', body: { reason, business_date: businessDate, amount },
    }),
    onSuccess: invalidate,
  });
}
