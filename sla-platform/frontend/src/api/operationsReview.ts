import client from "./client";

export interface ReviewOverviewResponse {
  scope_queues: string[];
  top_loss_queues: Array<{
    queue: string; total_wall_hours: number; no_owner_hours: number;
    distinct_tickets: number; share_of_total_pct: number;
  }>;
  parking_lots: Array<{
    queue: string; no_owner_hours: number; no_owner_pct: number; distinct_tickets: number;
  }>;
  dying_in_queue: Array<{
    ticket_id: number; ticket_number: string; current_queue: string;
    current_owner: string | null; current_state: string;
    total_wall_hours: number; queues_visited: number; segments: number;
  }>;
  silent_breaches: Array<Record<string, unknown>>;
  hot_potato: Array<{
    ticket_id: number; ticket_number: string;
    moves: number; owner_changes: number; distinct_queues: number;
  }>;
  overloaded_engineers: Array<Record<string, unknown>>;
  hidden_breach_delta: {
    wall_breaches: number; active_breaches: number; hidden_breaches: number;
  };
}

export interface EngineerLoadRow {
  owner: string;
  tickets: number;
  hours_owned: number;
  overload_ratio: number;
  distinct_queues: number;
  spof_risk_queues: number;
  spof_queue_names: string[];
  reassign_pressure: number;
  load_balance_score: number;
  flag_overloaded: boolean;
  flag_spof: boolean;
}

export interface EngineerLoadResponse {
  threshold_ratio: number;
  scope_queues: string[];
  engineer_count: number;
  flagged_count: number;
  engineers: EngineerLoadRow[];
  flagged_engineers: EngineerLoadRow[];
}

export interface QueueProfile {
  queue: string;
  total_tickets: number;
  open_now: number;
  metrics: Record<string, {
    n: number; breaches: number; breach_pct: number; avg_seconds: number;
  }>;
  no_owner_pct: number;
  total_owned_hours: number;
  no_owner_hours: number;
}

export interface QueueComparisonResponse {
  a: QueueProfile;
  b: QueueProfile;
  delta: Record<string, { a: number; b: number; delta: number }>;
}

export const operationsReviewApi = {
  reviewOverview: (queues?: string[]) =>
    client.get<ReviewOverviewResponse>("/operations/review/overview", {
      params: queues && queues.length ? { queue: queues } : {},
    }).then(r => r.data),

  engineerLoad: (threshold = 2.0, queues?: string[]) =>
    client.get<EngineerLoadResponse>("/operations/engineer-load/overload-risk", {
      params: { threshold_ratio: threshold, ...(queues && queues.length ? { queue: queues } : {}) },
    }).then(r => r.data),

  compareQueues: (queueA: string, queueB: string) =>
    client.get<QueueComparisonResponse>(
      `/operations/comparison/${encodeURIComponent(queueA)}/vs/${encodeURIComponent(queueB)}`
    ).then(r => r.data),
};
