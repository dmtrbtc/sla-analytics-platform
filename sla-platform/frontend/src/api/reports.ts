import client from "./client";

type ScopeParams = Record<string, string | undefined>;

export const reportsApi = {
  list: () => client.get("/reports"),
  get: (id: string) => client.get(`/reports/${id}`),
  /**
   * Trigger a Celery report. Pass `scope` (from `useTimeScope().toParams()`)
   * to constrain the generated report to a window — the worker resolves it
   * through `parse_time_scope`. Without scope, the report covers all-time
   * (or the legacy 30-day default for the executive report).
   */
  generate: (params: Record<string, unknown>, scope?: ScopeParams) =>
    client.post("/reports/generate", null, { params: { ...params, ...(scope || {}) } }),
  status: (taskId: string) => client.get(`/reports/status/${taskId}`),
  download: (filename: string) =>
    client.get(`/reports/${filename}/download`, { responseType: "blob" }),
};
