import { create } from "zustand";

export interface Notification {
  id: string;
  title: string;
  message: string;
  level: "info" | "warning" | "error" | "success";
  action_url?: string;
  timestamp: number;
  read: boolean;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  showBadge: boolean;
  addNotification: (n: Notification) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  showBadge: true,

  addNotification: (n) => {
    const updated = [n, ...get().notifications].slice(0, 100);
    set({
      notifications: updated,
      unreadCount: updated.filter((x) => !x.read).length,
    });
  },

  markRead: (id) => {
    const updated = get().notifications.map((n) =>
      n.id === id ? { ...n, read: true } : n
    );
    set({
      notifications: updated,
      unreadCount: updated.filter((x) => !x.read).length,
    });
  },

  markAllRead: () => {
    set({
      notifications: get().notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    });
  },

  clearAll: () => {
    set({ notifications: [], unreadCount: 0 });
  },
}));
