import client from './client';

type ScopeParams = Record<string, string | undefined>;

export interface ForensicQueueRow {
  queue: string;
  total_tickets: number;
  total_wall_hours: number;
  mean_stay_hours: number;
  p90_stay_hours: number;
  no_owner_ratio: number;
  touch_rate_per_hour: number;
  entropy_bits: number;
  unique_targets: number;
  routing_chaos_score: number;
  parking_lot_score: number;
  black_hole_score: number;
  stagnation_score: number;
  transfer_loop_score: number;
  pressure_score: number;
  breach_count: number;
  breach_rate: number;
}

export interface ForensicOwnerRow {
  owner: string;
  load_tickets: number;
  load_hours: number;
  parked_tickets: number;
  ownership_gap_seconds: number;
  non_sys_events: number;
  touch_frequency: number;
  reassignment_pressure: number;
  overload_score: number;
  idle_flag: boolean;
}

export interface ForensicTransition {
  src: string; dst: string; count: number; tickets: number;
}

export interface HotPotatoTicket {
  ticket_id: number;
  ticket_number: string | null;
  current_queue: string | null;
  current_state: string | null;
  moves: number;
  owner_changes: number;
  distinct_queues: number;
}

export interface SilentBreachTicket {
  ticket_id: number;
  ticket_number: string | null;
  queue_name: string | null;
  owner: string | null;
  state_name: string | null;
  last_activity_age_seconds: number;
  sla_target_seconds: number;
  inactivity_ratio: number;
  silent_breach_probability: number;
  risk_level: string;
}

export interface QueueSilenceRow {
  queue: string;
  open_tickets: number;
  median_age_seconds: number;
  p90_age_seconds: number;
  silence_score: number;
}

export interface ForensicSummary {
  kpis: {
    pause_total: number; idle_total: number; no_owner_total: number;
    gap_total: number; xfer_total: number; stag_total: number;
    wall_total: number; wall_breached: number; active_breached: number;
  };
  queues_top_blackholes: ForensicQueueRow[];
  queues_top_chaos: ForensicQueueRow[];
  queues_top_breach: ForensicQueueRow[];
  owners_top_load: ForensicOwnerRow[];
  owners_idle: ForensicOwnerRow[];
  transitions: ForensicTransition[];
  hot_potato: HotPotatoTicket[];
  silent_breaches: SilentBreachTicket[];
  queue_silence: QueueSilenceRow[];
}

/**
 * Every list/aggregate endpoint accepts an optional `scope` object built by
 * `useTimeScope().toParams()`. The per-ticket attribution endpoint is
 * scope-agnostic (whole lifecycle).
 */
export const forensicsApi = {
  summary: (queues?: string[], scope?: ScopeParams) =>
    client.get<ForensicSummary>('/analytics/forensics/summary', {
      params: {
        ...(queues && queues.length ? { queue: queues } : {}),
        ...(scope || {}),
      },
    }).then(r => r.data),

  queues: (sortBy = 'black_hole_score', limit = 100, scope?: ScopeParams) =>
    client.get('/analytics/forensics/queues', { params: { sort_by: sortBy, limit, ...(scope || {}) } })
      .then(r => r.data as { count: number; queues: ForensicQueueRow[] }),

  owners: (limit = 100, scope?: ScopeParams) =>
    client.get('/analytics/forensics/owners', { params: { limit, ...(scope || {}) } }).then(r => r.data),

  transitions: (limit = 200, scope?: ScopeParams) =>
    client.get('/analytics/forensics/transitions', { params: { limit, ...(scope || {}) } })
      .then(r => r.data as { count: number; transitions: ForensicTransition[] }),

  hotPotato: (minMoves = 3, limit = 50, scope?: ScopeParams) =>
    client.get('/analytics/forensics/hot-potato', { params: { min_moves: minMoves, limit, ...(scope || {}) } })
      .then(r => r.data as { count: number; tickets: HotPotatoTicket[] }),

  blackholes: (minScore = 0.3, scope?: ScopeParams) =>
    client.get('/analytics/forensics/blackholes', { params: { min_score: minScore, ...(scope || {}) } })
      .then(r => r.data as { count: number; queues: ForensicQueueRow[] }),

  stagnation: (scope?: ScopeParams) =>
    client.get('/analytics/forensics/stagnation', { params: { ...(scope || {}) } }).then(r => r.data),

  silentBreaches: (minRatio = 0.5, limit = 200, scope?: ScopeParams) =>
    client.get('/analytics/forensics/silent-breaches', { params: { min_ratio: minRatio, limit, ...(scope || {}) } })
      .then(r => r.data as { count: number; tickets: SilentBreachTicket[]; queue_silence: QueueSilenceRow[] }),

  ticketAttribution: (ticketId: number, metric: 'resolution_time' | 'first_response_time' = 'resolution_time') =>
    client.get(`/analytics/forensics/tickets/${ticketId}/attribution`, { params: { metric } })
      .then(r => r.data),

  breaches: (metric: 'resolution_time' | 'first_response_time' = 'resolution_time', limit = 100, scope?: ScopeParams) =>
    client.get('/analytics/forensics/breaches', { params: { metric, limit, ...(scope || {}) } }).then(r => r.data),
};

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0с';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h >= 24) {
    const d = Math.floor(h / 24);
    const rh = h % 24;
    return rh ? `${d}д ${rh}ч` : `${d}д`;
  }
  if (h > 0) return m ? `${h}ч ${m}м` : `${h}ч`;
  if (m > 0) return `${m}м`;
  return `${Math.round(seconds)}с`;
}
