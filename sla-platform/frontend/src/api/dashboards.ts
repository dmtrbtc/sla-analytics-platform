import client from "./client";

export const dashboardsApi = {
  overview: (params?: Record<string, unknown>) =>
    client.get("/dashboards/overview", { params }),
  timeSeries: (params?: Record<string, unknown>) =>
    client.get("/dashboards/time-series", { params }),
  teamsAnalytics: (params?: Record<string, unknown>) =>
    client.get("/dashboards/teams", { params }),
  ticketFlow: (params?: Record<string, unknown>) =>
    client.get("/dashboards/ticket-flow", { params }),
  slaTrend: (params?: Record<string, unknown>) =>
    client.get("/dashboards/sla-trend", { params }),
  byQueue: () => client.get("/dashboards/by-queue"),
  reassignments: () => client.get("/dashboards/reassignments"),
  approachingBreach: () => client.get("/dashboards/approaching-breach"),

  // Phase 5D: Advanced Analytics
  slaForecast: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/sla-forecast", { params }),
  queueOverload: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/queue-overload", { params }),
  reassignmentAnalysis: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/reassignments", { params }),
  agentWorkload: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/agent-workload", { params }),
  problematicQueues: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/problematic-queues", { params }),
  mttrMtta: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/mttr-mtta", { params }),
  agingTickets: () => client.get("/dashboards/analytics/aging-tickets"),
  ftrRate: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/ftr-rate", { params }),
  reopenRate: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/reopen-rate", { params }),
  breachRootCause: (params?: Record<string, unknown>) =>
    client.get("/dashboards/analytics/breach-root-cause", { params }),
};
