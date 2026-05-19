import client from "./client";

export const ticketsApi = {
  list: (params?: Record<string, unknown>) =>
    client.get("/tickets", { params }),
  get: (id: number) => client.get(`/tickets/${id}`),
  timeline: (id: number) => client.get(`/tickets/${id}/timeline`),
  ownership: (id: number) => client.get(`/tickets/${id}/ownership`),
  queuePeriods: (id: number) => client.get(`/tickets/${id}/queue-periods`),
  sla: (id: number) => client.get(`/tickets/${id}/sla`),
  slaTimeline: (id: number) => client.get(`/sla/timeline/${id}`),
  slaMetrics: (ticketId: number) => client.get("/sla/v2/metrics", { params: { ticket_id: ticketId } }),
  slaBreachEta: (ticketId: number, metricName: string = "first_response_time") =>
    client.get("/sla/predictive/breach-eta", { params: { ticket_id: ticketId, metric_name: metricName } }),
};
