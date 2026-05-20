import client from "./client";

export const analyticsApi = {
  overview: (params?: Record<string, unknown>) =>
    client.get("/analytics/overview", { params }),
  queueHeatmap: (params?: Record<string, unknown>) =>
    client.get("/analytics/queue-heatmap", { params }),
  bottlenecks: (params?: Record<string, unknown>) =>
    client.get("/analytics/bottlenecks", { params }),
  slaRisks: (params?: Record<string, unknown>) =>
    client.get("/analytics/sla-risks", { params }),
  trends: (params?: Record<string, unknown>) =>
    client.get("/analytics/trends", { params }),
  forecast: (params?: Record<string, unknown>) =>
    client.get("/analytics/forecast", { params }),
  correlations: () =>
    client.get("/analytics/correlations"),
  costs: () =>
    client.get("/analytics/costs"),
  queueSaturation: (params?: Record<string, unknown>) =>
    client.get("/analytics/queue-saturation", { params }),
  materializedViews: () =>
    client.get("/analytics/materialized-views/status"),
  refreshMaterializedViews: () =>
    client.post("/analytics/materialized-views/refresh"),
};

export async function fetchExecutiveOverview(period = "daily") {
  const { data } = await client.get("/ai/executive-summary", { params: { period } });
  return data;
}

export async function fetchLiveHealth() {
  const { data } = await client.get("/system/health");
  return data;
}

export async function fetchDiagnostics() {
  const { data } = await client.get("/system/diagnostics");
  return data;
}

export async function fetchTraces(limit = 100, traceId?: string) {
  const params: any = { limit };
  if (traceId) params.trace_id = traceId;
  const { data } = await client.get("/system/traces", { params });
  return data;
}

export async function copilotQuery(question: string) {
  const { data } = await client.post("/ai/copilot/query", { question });
  return data;
}

export async function fetchCopilotQueries() {
  const { data } = await client.get("/ai/copilot/queries");
  return data;
}

export async function triggerAutoMitigate() {
  const { data } = await client.post("/ops/auto-mitigate");
  return data;
}
