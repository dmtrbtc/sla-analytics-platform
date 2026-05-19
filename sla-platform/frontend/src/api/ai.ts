import client from "./client";

export const aiApi = {
  predict: (ticketId: number) =>
    client.get(`/ai/predict/${ticketId}`),
  predictBatch: (ticketIds: number[]) =>
    client.post("/ai/predict/batch", ticketIds),
  anomalies: (days?: number) =>
    client.get("/ai/anomalies", { params: { days } }),
  staffing: (days?: number) =>
    client.get("/ai/staffing", { params: { days } }),
  hints: (days?: number) =>
    client.get("/ai/hints", { params: { days } }),
};
