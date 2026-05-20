import client from "./client";

export const attachmentsApi = {
  upload: (file: File, ticketId?: number, importId?: string, description?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (ticketId) formData.append("ticket_id", String(ticketId));
    if (importId) formData.append("import_id", importId);
    if (description) formData.append("description", description);
    return client.post("/attachments/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e: any) => {
        if (e.total) console.debug(`Upload: ${Math.round((e.loaded / e.total) * 100)}%`);
      },
    });
  },
  list: (params?: { ticket_id?: number; import_id?: string; limit?: number; offset?: number }) =>
    client.get("/attachments", { params }),
  get: (id: string) => client.get(`/attachments/${id}`, { responseType: "blob" }),
  delete: (id: string) => client.delete(`/attachments/${id}`),
};
