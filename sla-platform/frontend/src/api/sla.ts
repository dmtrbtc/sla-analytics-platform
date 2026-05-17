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
