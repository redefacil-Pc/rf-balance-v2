import { useMutation, useQueryClient } from '@tanstack/react-query';

import { proposalKeys } from '@/features/proposals/queries/proposal-keys';
import type { ProposalForm } from '@/features/proposals/schemas/proposal-schema';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ProposalWriteResult } from '@/shared/types/commercial';

export function useCreateProposal() {
  const client = useQueryClient();

  return useMutation<ProposalWriteResult, ApiError, ProposalForm>({
    mutationFn: (form) =>
      requisitar<ProposalWriteResult>('/proposals', {
        method: 'POST',
        body: {
          consultant_id: form.consultant_id,
          business_date: form.business_date,
          customer_name: form.customer_name,
          customer_document: form.customer_document,
          // string decimal: a comissão quem calcula é o servidor
          operation_amount: form.operation_amount,
          tps_percentage: form.tps_percentage,
          external_id: form.external_id || null,
          bko_collaborator_id: form.bko_collaborator_id,
          finalizer_collaborator_id: form.finalizer_collaborator_id,
        },
      }),
    onSuccess: () => {
      // invalida por prefixo: qualquer combinação de filtro é refeita
      void client.invalidateQueries({ queryKey: proposalKeys.todos });
    },
  });
}

export interface InitialReceiptInput {
  amount: string;
  businessDate: string;
  paymentTime: string;
  paymentMethod: string;
  receivingAccountId: number;
  proof: File;
  idempotencyKey: string;
}

interface CreateProposalWithReceiptInput {
  form: ProposalForm;
  receipt: InitialReceiptInput;
}

export function useCreateProposalWithReceipt() {
  const client = useQueryClient();

  return useMutation<
    ProposalWriteResult & { receipt_id: number },
    ApiError,
    CreateProposalWithReceiptInput
  >({
    mutationFn: ({ form, receipt }) => {
      const body = new FormData();
      body.set('consultant_id', String(form.consultant_id));
      body.set('proposal_business_date', form.business_date);
      body.set('customer_name', form.customer_name);
      body.set('customer_document', form.customer_document);
      body.set('operation_amount', form.operation_amount);
      body.set('tps_percentage', form.tps_percentage);
      if (form.external_id) body.set('external_id', form.external_id);
      if (form.bko_collaborator_id !== null) {
        body.set('bko_collaborator_id', String(form.bko_collaborator_id));
      }
      if (form.finalizer_collaborator_id !== null) {
        body.set('finalizer_collaborator_id', String(form.finalizer_collaborator_id));
      }
      body.set('amount', receipt.amount);
      body.set('payment_business_date', receipt.businessDate);
      if (receipt.paymentTime) body.set('payment_time', receipt.paymentTime);
      body.set('payment_method', receipt.paymentMethod);
      body.set('receiving_account_id', String(receipt.receivingAccountId));
      body.set('proof', receipt.proof);
      return requisitar<ProposalWriteResult & { receipt_id: number }>(
        '/proposals/with-receipt',
        { method: 'POST', body, idempotencyKey: receipt.idempotencyKey },
      );
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: proposalKeys.todos });
      void client.invalidateQueries({ queryKey: ['receipts'] });
    },
  });
}
