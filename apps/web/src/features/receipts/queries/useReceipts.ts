import { useQuery } from '@tanstack/react-query';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';
import type { ReceiptPage, ReceiptStatus } from '@/shared/types/receipts';

export const receiptKeys = { all: ['receipts'] as const };

export function useReceipts(status?: ReceiptStatus) {
  const query = status ? `?status=${status}` : '';
  return useQuery<ReceiptPage, ApiError>({
    queryKey: [...receiptKeys.all, status],
    queryFn: ({ signal }) => requisitar<ReceiptPage>(`/receipts${query}`, { signal }),
  });
}
