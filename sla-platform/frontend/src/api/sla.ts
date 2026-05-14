import client from "./client";

export const slaApi = {
  listDefinitions: () => client.get("/sla/definitions"),
  getDefinition: (id: number) => client.get(`/sla/definitions/${id}`),
  createDefinition: (data: Record<string, unknown>) =>
    client.post("/sla/definitions", data),
  updateDefinition: (id: number, data: Record<string, unknown>) =>
    client.put(`/sla/definitions/${id}`, data),
  deleteDefinition: (id: number) => client.delete(`/sla/definitions/${id}`),
  listBreaches: () => client.get("/sla/breaches"),
};
