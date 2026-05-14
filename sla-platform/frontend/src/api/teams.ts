import client from "./client";

export const teamsApi = {
  list: (params?: Record<string, unknown>) =>
    client.get("/teams", { params }),
  get: (id: number) => client.get(`/teams/${id}`),
  create: (data: Record<string, unknown>) => client.post("/teams", data),
  update: (id: number, data: Record<string, unknown>) =>
    client.put(`/teams/${id}`, data),
  delete: (id: number) => client.delete(`/teams/${id}`),
};
