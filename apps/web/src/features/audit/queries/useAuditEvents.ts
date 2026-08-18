import { useInfiniteQuery, useQuery } from '@tanstack/react-query';

import type { AuditEventPage, AuditOptions } from '@/features/audit/types';
import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export interface AuditFilters {
  start_date: string;
  end_date: string;
  module?: string;
  action?: string;
  actor?: string;
  aggregate_type?: string;
  aggregate_id?: string;
  correlation_id?: string;
}

function params(filters: AuditFilters, cursor: string | null): string {
  const result = new URLSearchParams({
    start_date: filters.start_date,
    end_date: filters.end_date,
    limit: '30',
  });
  for (const [key, value] of Object.entries(filters)) {
    if (value) result.set(key, value);
  }
  if (cursor) result.set('cursor', cursor);
  return result.toString();
}

export function useAuditEvents(filters: AuditFilters) {
  return useInfiniteQuery<AuditEventPage, ApiError>({
    queryKey: ['audit-events', filters],
    queryFn: ({ pageParam, signal }) =>
      requisitar<AuditEventPage>(`/audit-events?${params(filters, pageParam as string | null)}`, {
        signal,
      }),
    initialPageParam: null,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useAuditOptions() {
  return useQuery<AuditOptions, ApiError>({
    queryKey: ['audit-events', 'options'],
    queryFn: ({ signal }) => requisitar<AuditOptions>('/audit-events/options', { signal }),
  });
}
