import client from "./client";

export interface Incident {
  id: string;
  type: string;
  severity: string;
  title: string;
  summary: string;
  queue: string;
  source: string;
  status: string;
  created_at: string;
  updated_at: string;
  resolution?: string;
  resolved_at?: string;
}

export const incidentsApi = {
  list: (params?: Record<string, unknown>) =>
    client.get("/ops/incidents", { params }),
  create: (data: Record<string, unknown>) =>
    client.post("/ops/incidents", data),
  get: (id: string) =>
    client.get(`/ops/incidents/${id}`),
  acknowledge: (id: string) =>
    client.post(`/ops/incidents/${id}/acknowledge`),
  resolve: (id: string, data?: Record<string, unknown>) =>
    client.post(`/ops/incidents/${id}/resolve`, data),
  addComment: (id: string, data: Record<string, string>) =>
    client.post(`/ops/incidents/${id}/comments`, data),
  detect: () =>
    client.get("/ops/incidents/detect"),
};
