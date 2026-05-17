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
};
