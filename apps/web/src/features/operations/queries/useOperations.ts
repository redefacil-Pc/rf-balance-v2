import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export interface BackupSummary {
  key: string;
  created_at: string;
  compressed_bytes: number;
  sha256: string | null;
  verified: boolean;
}

export interface IntegrityCheckSummary {
  check_type: string;
  status: 'PASS' | 'FAIL';
  count: number;
  checked_at: string;
}

export interface OperationsStatus {
  backup: {
    enabled: boolean;
    prefix: string;
    retention_days: number;
    schedule_hour_utc: number;
    last_backup: BackupSummary | null;
    versioning_enabled: boolean;
    local_replica_enabled: boolean;
  };
  integrity_checks: IntegrityCheckSummary[];
}

export interface BackupExecution {
  key: string;
  created_at: string;
  compressed_bytes: number;
  sha256: string;
  removed_by_retention: number;
  local_replica_created: boolean;
}

const key = ['admin-operations'] as const;

export function useOperationsStatus() {
  return useQuery<OperationsStatus, ApiError>({
    queryKey: key,
    queryFn: ({ signal }) => requisitar('/admin/operations', { signal }),
    refetchInterval: 60_000,
  });
}

export function useRunBackup() {
  const client = useQueryClient();
  return useMutation<BackupExecution, ApiError>({
    mutationFn: () => requisitar('/admin/operations/backups', { method: 'POST' }),
    onSuccess: async () => client.invalidateQueries({ queryKey: key }),
  });
}
