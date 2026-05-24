import client from "./client";

type ScopeParams = Record<string, string | undefined>;

export interface QueueCCMetric {
  n: number;
  breaches: number;
  breach_pct: number;
  avg_seconds: number;
  p50_seconds: number;
  p90_seconds: number;
}

export interface QueueCCEngineer {
  owner: string;
  tickets_held: number;
  hours_owned: number | string;
}

export interface QueueCCAgingTicket {
  ticket_id: number;
  ticket_number: string;
  title: string | null;
  current_owner: string | null;
  current_state: string;
  age_days: number;
  first_response_at: string | null;
}

export interface QueueCommandCenterResponse {
  queue_name: string;
  snapshot: {
    total: number;
    open_now: number;
    closed_now: number;
    open_no_owner: number;
    with_first_response: number;
    open_over_7d: number;
    open_over_30d: number;
  };
  sla_metrics: Record<
    "first_response_time" | "resolution_time" |
    "wall_response_time"  | "wall_resolution_time",
    QueueCCMetric
  >;
  engineers: QueueCCEngineer[];
  aging_open_tickets: QueueCCAgingTicket[];
  hour_distribution: Array<{ hour: number; tickets: number }>;
  dow_distribution: Array<{ dow: number; tickets: number }>;
  transitions: {
    outbound: Array<{ dest_queue: string; n: number; tickets: number }>;
    inbound:  Array<{ src_queue: string;  n: number; tickets: number }>;
  };
  bounces: Array<{ ticket_id: number; visits: number }>;
  silent_breaches: Array<Record<string, unknown>>;
  loss_share: {
    queue: string;
    total_wall_hours: number;
    no_owner_hours: number;
    share_of_total_pct: number;
    distinct_tickets: number;
  } | null;
}

export const queueCommandCenterApi = {
  /**
   * Per-queue command center. Optional `scope` object comes from
   * `useTimeScope().toParams()` and propagates the global toolbar window
   * to every chart on the page. When `scope` is omitted, the backend
   * falls back to all-time aggregation.
   */
  get: (queueName: string, scope?: ScopeParams) =>
    client.get<QueueCommandCenterResponse>(
      `/operations/queue-command-center/${encodeURIComponent(queueName)}`,
      { params: { ...(scope || {}) } },
    ).then(r => r.data),
};
