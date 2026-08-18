import { useMutation, useQueryClient } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ReceiptWriteResult } from '@/shared/types/receipts';

export interface CreateReceiptInput {
  proposalId: number;
  amount: string;
  businessDate: string;
  paymentTime: string;
  paymentMethod: string;
  receivingAccountId: number | null;
  reference: string;
  notes: string;
  proof: File;
  idempotencyKey: string;
}

export function useCreateReceipt() {
  const client = useQueryClient();
  return useMutation<ReceiptWriteResult, ApiError, CreateReceiptInput>({
    mutationFn: (input) => {
      const body = new FormData();
      body.set('amount', input.amount);
      body.set('business_date', input.businessDate);
      if (input.paymentTime) body.set('payment_time', input.paymentTime);
      body.set('payment_method', input.paymentMethod);
      // omitido quando não escolhido: enviar vazio viraria erro de tipo no Form
      if (input.receivingAccountId !== null) {
        body.set('receiving_account_id', String(input.receivingAccountId));
      }
      body.set('reference', input.reference);
      body.set('notes', input.notes);
      body.set('proof', input.proof);
      return requisitar(`/proposals/${input.proposalId}/receipts`, {
        method: 'POST',
        body,
        idempotencyKey: input.idempotencyKey,
      });
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['receipts'] });
      void client.invalidateQueries({ queryKey: ['proposals'] });
    },
  });
}
