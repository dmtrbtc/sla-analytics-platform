import client from "./client";

export const teamsApi = {
  list: (activeOnly = false) => client.get("/teams", { params: { active_only: activeOnly } }),
  get: (id: number) => client.get(`/teams/${id}`),
  create: (data: { name: string; queue_prefix?: string; description?: string }) => client.post("/teams", data),
  update: (id: number, data: { name?: string; queue_prefix?: string; description?: string; is_active?: boolean }) => client.put(`/teams/${id}`, data),
  delete: (id: number) => client.delete(`/teams/${id}`),
};
