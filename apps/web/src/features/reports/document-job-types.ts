export type DocumentJobStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'FAILED'
  | 'COMPLETED'
  | 'DEAD_LETTER';

export interface DocumentJob {
  id: number;
  job_type: string;
  status: DocumentJobStatus;
  period_start: string;
  period_end: string;
  unit_id: number | null;
  leader_id: number | null;
  total_items: number;
  processed_items: number;
  attempt_count: number;
  max_attempts: number;
  error_message: string | null;
  archive_ready: boolean;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface DocumentJobPage {
  items: DocumentJob[];
}
