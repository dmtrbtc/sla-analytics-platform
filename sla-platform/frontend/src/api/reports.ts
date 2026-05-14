import client from "./client";

export const reportsApi = {
  list: () => client.get("/reports"),
  get: (id: string) => client.get(`/reports/${id}`),
  generate: (params: Record<string, unknown>) =>
    client.post("/reports/generate", null, { params }),
  status: (taskId: string) => client.get(`/reports/status/${taskId}`),
  download: (filename: string) =>
    client.get(`/reports/${filename}/download`, { responseType: "blob" }),
};
