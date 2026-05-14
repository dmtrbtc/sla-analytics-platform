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
  slaTrend: () => client.get("/dashboards/sla-trend"),
  byQueue: () => client.get("/dashboards/by-queue"),
  reassignments: () => client.get("/dashboards/reassignments"),
  approachingBreach: () => client.get("/dashboards/approaching-breach"),
};
