import { useCallback, useEffect, useRef } from "react";
import { useAuthStore } from "../stores/authStore";
import { useNotificationStore } from "../stores/notificationStore";

type WSEventHandler = (data: Record<string, unknown>) => void;

const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const MAX_RECONNECT_ATTEMPTS = 10;

const handlers: Record<string, WSEventHandler[]> = {};

export function onWsEvent(type: string, handler: WSEventHandler) {
  if (!handlers[type]) handlers[type] = [];
  handlers[type].push(handler);
  return () => {
    handlers[type] = handlers[type].filter((h) => h !== handler);
  };
}

const globalListeners: Array<() => void> = [];

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isConnected = useRef(false);
  const token = useAuthStore((s) => s.token);
  const addNotification = useNotificationStore((s) => s.addNotification);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempt.current >= MAX_RECONNECT_ATTEMPTS) {
      console.warn("[WS] Max reconnect attempts reached");
      return;
    }
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** reconnectAttempt.current,
      RECONNECT_MAX_MS
    );
    reconnectAttempt.current += 1;
    reconnectTimer.current = setTimeout(connect, delay);
  }, []);

  const connect = useCallback(() => {
    if (!token) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = `${WS_URL}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      isConnected.current = true;
      reconnectAttempt.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const type = data.type as string;
        if (type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          return;
        }
        if (type === "notification") {
          addNotification({
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            title: data.title as string,
            message: data.message as string,
            level: (data.level as "info" | "warning" | "error" | "success") || "info",
            action_url: data.action_url as string | undefined,
            timestamp: (data.ts as number) || Date.now(),
            read: false,
          });
        }
        const eventHandlers = handlers[type];
        if (eventHandlers) {
          eventHandlers.forEach((h) => h(data as Record<string, unknown>));
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      isConnected.current = false;
      wsRef.current = null;
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [token, addNotification, scheduleReconnect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      isConnected.current = false;
    };
  }, [connect]);

  return {
    isConnected: () => isConnected.current,
    reconnect: connect,
  };
}
