import client from "./client";

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
};
