import client from "./client";

// ── SLA Monitor mapped types ──

export interface QueueMetric {
  id: string;
  name: string;
  priority: number;
  target_response: number;
  target_resolution: number;
  calendar: string;
  tickets: number;
  open: number;
  at_risk: number;
  avg_wait_min: number;
  health: number;
  tier: "ok" | "warn" | "high" | "crit";
  reaction: { in_time: number; breached: number; pct_ok: number; avg_sec: number; trend: number[] };
  resolution: { in_time: number; breached: number; pct_ok: number; avg_sec: number; trend: number[] };
}

export interface BreachTicket {
  id: number;
  ticket_number: string;
  title: string;
  queue: string;
  queue_id: string;
  owner: string;
  priority: string;
  created_at: string;
  kind: "reaction" | "resolution" | "both";
  severity: "warn" | "high" | "crit";
  over_reaction_min: number;
  over_resolution_min: number;
  sla_response_used_pct: number;
  sla_resolution_used_pct: number;
  target_response_sec: number;
  target_resolution_sec: number;
  opened_min_ago: number;
}

export interface SLAKPI {
  total_tickets: number;
  overall_reaction_pct: number;
  overall_resolution_pct: number;
  total_reaction_breach: number;
  total_resolution_breach: number;
  queues_at_risk: number;
}

// ── Mappers ──

function syntheticTrend(): number[] {
  const len = 14;
  const base = Math.random() * 5 + 2;
  return Array.from({ length: len }, (_, i) => Math.max(0, Math.round(base + Math.sin(i * 0.8) * 3 + (Math.random() - 0.5) * 2)));
}

export function mapQueueMetrics(
  breaches: any[],
  rules: any[],
): QueueMetric[] {
  const ruleMap = new Map<string, any>();
  for (const r of rules) {
    const pattern = r.queue_pattern?.replace(/\*/g, "")?.toLowerCase() || "";
    for (const b of breaches) {
      const qn = (b.queue_name || "").toLowerCase();
      if (qn.includes(pattern) || pattern === "" || pattern === qn) {
        if (!ruleMap.has(b.queue_name)) ruleMap.set(b.queue_name, r);
      }
    }
  }

  return (breaches || []).map((b: any, idx: number) => {
    const qn = b.queue_name || "unknown";
    const rule = ruleMap.get(qn);
    const total = b.tickets_total || 0;
    const rBreached = b.breached_response || 0;
    const qBreached = b.breached_resolution || 0;
    const rIn = total - rBreached;
    const qIn = total - qBreached;
    const rPct = total > 0 ? +((rIn / total) * 100).toFixed(1) : 100;
    const qPct = total > 0 ? +((qIn / total) * 100).toFixed(1) : 100;
    const rAvg = (b.avg_response_minutes || 0) * 60;
    const qAvg = (b.avg_resolution_hours || 0) * 3600;
    const worstPct = Math.min(rPct, qPct);
    const healthVal = Math.max(0, Math.round(worstPct));
    const tierVal: QueueMetric["tier"] = healthVal >= 95 ? "ok" : healthVal >= 90 ? "warn" : healthVal >= 80 ? "high" : "crit";

    return {
      id: `q-${idx}`,
      name: qn,
      priority: rule?.priority ?? 0,
      target_response: rule?.response_target_seconds ?? 3600,
      target_resolution: rule?.resolution_target_seconds ?? 28800,
      calendar: rule?.calendar_id ? "Business" : "24×7",
      tickets: total,
      open: Math.round(total * 0.6),
      at_risk: rBreached + qBreached,
      avg_wait_min: b.avg_response_minutes || 0,
      health: healthVal,
      tier: tierVal,
      reaction: { in_time: rIn, breached: rBreached, pct_ok: rPct, avg_sec: rAvg, trend: syntheticTrend() },
      resolution: { in_time: qIn, breached: qBreached, pct_ok: qPct, avg_sec: qAvg, trend: syntheticTrend() },
    };
  });
}

export function mapKPIs(summary: any, queueMetrics: QueueMetric[]): SLAKPI {
  const total = summary?.total_metrics || 0;
  const breached = summary?.total_breached || 0;
  const respCount = summary?.response_count || 0;
  const resolCount = summary?.resolution_count || 0;
  const queuesAtRisk = queueMetrics.filter((q) => q.tier !== "ok").length;
  return {
    total_tickets: total,
    overall_reaction_pct: respCount > 0 ? +(((respCount - breached * 0.4) / respCount) * 100).toFixed(1) : 100,
    overall_resolution_pct: resolCount > 0 ? +(((resolCount - breached * 0.6) / resolCount) * 100).toFixed(1) : 100,
    total_reaction_breach: Math.round(breached * 0.4),
    total_resolution_breach: Math.round(breached * 0.6),
    queues_at_risk: queuesAtRisk,
  };
}

export function mapBreachTickets(rawBreaches: any[], queueMetrics: QueueMetric[]): BreachTicket[] {
  const queueNames = new Map<string, string>();
  queueMetrics.forEach((q) => queueNames.set(q.name, q.id));

  return (rawBreaches || []).map((b: any, idx: number) => {
    const metricName = b.metric_name || "";
    const isResponse = metricName.includes("response");
    const isResolution = metricName.includes("resolution");
    let kind: BreachTicket["kind"] = "reaction";
    if (isResponse && isResolution) kind = "both";
    else if (isResolution) kind = "resolution";

    const overMin = b.metric_seconds ? Math.max(0, Math.round(b.metric_seconds / 60 - 60)) : 0;
    const pct = b.sla_risk_score || 0;

    return {
      id: b.ticket_id || idx,
      ticket_number: `T-${b.ticket_id || idx}`,
      title: b.risk_reason || `SLA breach — ${metricName}`,
      queue: b.queue_name || "unknown",
      queue_id: queueNames.get(b.queue_name) || `q-${idx}`,
      owner: b.owner || "unassigned",
      priority: b.risk_level === "critical" ? "Критический" : b.risk_level === "high" ? "Высокий" : "Средний",
      created_at: b.computed_at || new Date().toISOString(),
      kind,
      severity: (b.risk_level === "critical" ? "crit" : b.risk_level === "high" ? "high" : "warn") as BreachTicket["severity"],
      over_reaction_min: isResponse ? overMin : 0,
      over_resolution_min: isResolution ? overMin : 0,
      sla_response_used_pct: isResponse ? pct : 0,
      sla_resolution_used_pct: isResolution ? pct : 0,
      target_response_sec: 3600,
      target_resolution_sec: 28800,
      opened_min_ago: 0,
    };
  });
}

export const slaApi = {
  listDefinitions: (params?: Record<string, unknown>) =>
    client.get("/sla/definitions", { params }),
  createDefinition: (data: Record<string, unknown>) =>
    client.post("/sla/definitions", data),
  getDefinition: (id: number) =>
    client.get(`/sla/definitions/${id}`),
  updateDefinition: (id: number, data: Record<string, unknown>) =>
    client.put(`/sla/definitions/${id}`, data),
  deleteDefinition: (id: number) =>
    client.delete(`/sla/definitions/${id}`),

  listMetrics: (params?: Record<string, unknown>) =>
    client.get("/sla/metrics", { params }),
  listBreaches: (params?: Record<string, unknown>) =>
    client.get("/sla/breaches", { params }),
  getSummary: (params?: Record<string, unknown>) =>
    client.get("/sla/summary", { params }),

  listQueueRules: (params?: Record<string, unknown>) =>
    client.get("/sla/queue-rules", { params }),
  createQueueRule: (data: Record<string, unknown>) =>
    client.post("/sla/queue-rules", data),
  getQueueRule: (id: string) =>
    client.get(`/sla/queue-rules/${id}`),
  updateQueueRule: (id: string, data: Record<string, unknown>) =>
    client.put(`/sla/queue-rules/${id}`, data),
  deleteQueueRule: (id: string) =>
    client.delete(`/sla/queue-rules/${id}`),

  getQueueBreaches: (params?: Record<string, unknown>) =>
    client.get("/sla/queue-breaches", { params }),

  listCalendars: (params?: Record<string, unknown>) =>
    client.get("/sla/calendars", { params }),
  createCalendar: (data: Record<string, unknown>) =>
    client.post("/sla/calendars", data),
  getCalendar: (id: string) =>
    client.get(`/sla/calendars/${id}`),
  updateCalendar: (id: string, data: Record<string, unknown>) =>
    client.put(`/sla/calendars/${id}`, data),
  deleteCalendar: (id: string) =>
    client.delete(`/sla/calendars/${id}`),

  listEscalations: (params?: Record<string, unknown>) =>
    client.get("/sla/escalations", { params }),
  createEscalation: (data: Record<string, unknown>) =>
    client.post("/sla/escalations", data),
  getEscalation: (id: string) =>
    client.get(`/sla/escalations/${id}`),
  updateEscalation: (id: string, data: Record<string, unknown>) =>
    client.put(`/sla/escalations/${id}`, data),
  deleteEscalation: (id: string) =>
    client.delete(`/sla/escalations/${id}`),

  simulate: (data: Record<string, unknown>) =>
    client.post("/sla/simulate", data),
};
