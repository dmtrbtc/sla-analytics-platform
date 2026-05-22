import client from "./client";

export interface LossQueue {
  queue: string;
  segments?: number;
  distinct_tickets?: number;
  tickets?: number;
  total_wall_hours: number;
  mean_wall_minutes?: number;
  no_owner_hours?: number;
  no_owner_pct?: number;
  cost_per_ticket_hours?: number;
  share_of_total_pct?: number;
  total_owned_hours?: number;
}

export interface DyingTicket {
  ticket_id: number;
  ticket_number: string;
  title: string | null;
  current_queue: string;
  current_owner: string | null;
  current_state: string;
  total_wall_hours: number;
  queues_visited: number;
  segments: number;
}

export interface LossOverview {
  top_loss_queues: LossQueue[];
  most_expensive: LossQueue[];
  dying_in_queue: DyingTicket[];
  parking_lots: LossQueue[];
}

type ScopeParams = Record<string, string | undefined>;

export const slaLossApi = {
  overview: (queues?: string[], scope?: ScopeParams) =>
    client.get<LossOverview & { scope?: { label: string; since: string | null; until: string | null } }>(
      "/analytics/sla-loss/overview",
      { params: { ...(queues && queues.length ? { queue: queues } : {}), ...(scope || {}) } },
    ).then(r => r.data),

  topQueues: (limit = 25, days?: number, queues?: string[]) =>
    client.get<{ queues: LossQueue[] }>("/analytics/sla-loss/top-queues", {
      params: { limit, ...(days ? { days } : {}), ...(queues?.length ? { queue: queues } : {}) },
    }).then(r => r.data),

  mostExpensive: (limit = 25, queues?: string[]) =>
    client.get<{ queues: LossQueue[] }>("/analytics/sla-loss/most-expensive", {
      params: { limit, ...(queues?.length ? { queue: queues } : {}) },
    }).then(r => r.data),

  dyingInQueue: (limit = 25, queues?: string[]) =>
    client.get<{ tickets: DyingTicket[] }>("/analytics/sla-loss/dying-in-queue", {
      params: { limit, ...(queues?.length ? { queue: queues } : {}) },
    }).then(r => r.data),

  parkingLots: (limit = 25, queues?: string[]) =>
    client.get<{ queues: LossQueue[] }>("/analytics/sla-loss/parking-lots", {
      params: { limit, ...(queues?.length ? { queue: queues } : {}) },
    }).then(r => r.data),

  waterfall: (ticketId: number) =>
    client.get<{ ticket_id: number; segments: Array<{
      queue_name: string; entered_at: string | null; exited_at: string | null;
      minutes: number; cumulative_minutes: number;
    }>}>(`/analytics/sla-loss/waterfall/${ticketId}`).then(r => r.data),
};
