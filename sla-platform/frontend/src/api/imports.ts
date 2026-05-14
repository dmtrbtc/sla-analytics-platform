import client from "./client";

export interface ImportSession {
  id: string;
  status: string;
  backlog_file: string | null;
  history_file: string | null;
  backlog_rows: number | null;
  history_rows: number | null;
  stats: Record<string, unknown>;
  error_details: Array<{ step: string; message: string; timestamp: string }>;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export const importsApi = {
  list: () => client.get<ImportSession[]>("/imports/sessions"),
  get: (id: string) => client.get<ImportSession>(`/imports/sessions/${id}`),
  create: (formData: FormData) =>
    client.post<ImportSession>("/imports/sessions", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  start: (id: string) => client.post(`/imports/sessions/${id}/start`),
  reprocess: (id: string) => client.post(`/imports/sessions/${id}/reprocess`),
};
