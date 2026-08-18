export interface AuditEvent {
  id: number;
  occurred_at: string;
  business_date: string;
  module: string;
  action: string;
  actor_user_id: number | null;
  actor_name: string;
  aggregate_type: string | null;
  aggregate_id: string | null;
  correlation_id: string | null;
  payload: Record<string, unknown>;
}

export interface AuditEventPage {
  items: AuditEvent[];
  next_cursor: string | null;
}

export interface AuditOptions {
  modules: string[];
  actions: string[];
  aggregate_types: string[];
}
