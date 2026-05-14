import client from "./client";

export const ticketsApi = {
  list: (params?: Record<string, unknown>) =>
    client.get("/tickets", { params }),
  get: (id: number) => client.get(`/tickets/${id}`),
  timeline: (id: number) => client.get(`/tickets/${id}/timeline`),
  ownership: (id: number) => client.get(`/tickets/${id}/ownership`),
  queuePeriods: (id: number) => client.get(`/tickets/${id}/queue-periods`),
  sla: (id: number) => client.get(`/tickets/${id}/sla`),
};
