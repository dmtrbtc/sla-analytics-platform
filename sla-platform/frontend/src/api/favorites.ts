import client from "./client";

export interface FavoriteQueue {
  queue_name: string;
  position: number;
  starred_at: string | null;
}

export interface QueueGroup {
  id: string;
  user_id: string | null;
  name: string;
  description: string | null;
  color: string | null;
  is_shared: boolean;
  queues: string[];
  queue_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface DashboardPreset {
  id: string;
  user_id: string | null;
  name: string;
  workspace_kind: string;
  queue_group_id: string | null;
  layout: Record<string, unknown>;
  is_default: boolean;
  is_shared: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export const favoritesApi = {
  // Favorites
  list: () =>
    client.get<{ queues: FavoriteQueue[]; total: number }>("/favorites/queues").then(r => r.data),
  star: (queue_name: string) =>
    client.post("/favorites/queues", { queue_name }).then(r => r.data),
  unstar: (queue_name: string) =>
    client.delete(`/favorites/queues/${encodeURIComponent(queue_name)}`).then(r => r.data),
  reorder: (ordering: string[]) =>
    client.put("/favorites/queues/reorder", { ordering }).then(r => r.data),

  // Groups
  listGroups: (includeShared = true) =>
    client.get<{ groups: QueueGroup[]; total: number }>(
      "/favorites/groups", { params: { include_shared: includeShared } }
    ).then(r => r.data),
  getGroup: (id: string) =>
    client.get<QueueGroup>(`/favorites/groups/${id}`).then(r => r.data),
  createGroup: (data: { name: string; description?: string; color?: string; queues?: string[]; is_shared?: boolean }) =>
    client.post<QueueGroup>("/favorites/groups", data).then(r => r.data),
  updateGroup: (id: string, data: Partial<{ name: string; description: string; color: string; queues: string[]; is_shared: boolean }>) =>
    client.patch<QueueGroup>(`/favorites/groups/${id}`, data).then(r => r.data),
  deleteGroup: (id: string) =>
    client.delete(`/favorites/groups/${id}`).then(r => r.data),
  addQueueToGroup: (id: string, queue_name: string, position = 0) =>
    client.post(`/favorites/groups/${id}/queues`, { queue_name, position }).then(r => r.data),
  removeQueueFromGroup: (id: string, queue_name: string) =>
    client.delete(`/favorites/groups/${id}/queues/${encodeURIComponent(queue_name)}`).then(r => r.data),

  // Presets (workspaces)
  listPresets: (includeShared = true) =>
    client.get<{ presets: DashboardPreset[]; total: number }>(
      "/favorites/presets", { params: { include_shared: includeShared } }
    ).then(r => r.data),
  createPreset: (data: { name: string; workspace_kind: string; queue_group_id?: string; layout?: Record<string, unknown>; is_default?: boolean; is_shared?: boolean }) =>
    client.post<DashboardPreset>("/favorites/presets", data).then(r => r.data),
  updatePreset: (id: string, data: Partial<DashboardPreset>) =>
    client.patch<DashboardPreset>(`/favorites/presets/${id}`, data).then(r => r.data),
  deletePreset: (id: string) =>
    client.delete(`/favorites/presets/${id}`).then(r => r.data),
  markDefault: (id: string) =>
    client.post(`/favorites/presets/${id}/default`).then(r => r.data),
};

// Hook-friendly helper: serialize favorite queue names as repeated query params.
export function queuesQuery(queues: string[]): URLSearchParams {
  const p = new URLSearchParams();
  queues.forEach(q => p.append("queue", q));
  return p;
}
