import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { Period } from '@/features/settlements/queries/useSettlements';
import type { DocumentJob, DocumentJobPage } from '@/features/reports/document-job-types';
import type { FinancialReportScope } from '@/features/reports/queries/useFinancialReport';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

const key = ['document-jobs'] as const;

export function useDocumentJobs() {
  return useQuery<DocumentJobPage, ApiError>({
    queryKey: key,
    queryFn: ({ signal }) => requisitar('/document-jobs?limit=10', { signal }),
    refetchInterval: (query) => query.state.data?.items?.some(
      (item) => item.status === 'PENDING' || item.status === 'RUNNING' || item.status === 'FAILED',
    ) ? 2_000 : false,
  });
}

export function useCreateDocumentJob() {
  const client = useQueryClient();
  return useMutation<DocumentJob, ApiError, { period: Period; scope: FinancialReportScope }>({
    mutationFn: ({ period, scope }) => requisitar('/document-jobs', {
      method: 'POST',
      idempotencyKey: crypto.randomUUID(),
      body: { ...period, ...scope },
    }),
    onSuccess: async () => client.invalidateQueries({ queryKey: key }),
  });
}
