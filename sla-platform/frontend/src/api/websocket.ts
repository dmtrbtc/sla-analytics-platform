/** WebSocket connection manager with auto-reconnect. */
import { useCallback, useEffect, useRef, useState } from "react";

type WSEvent = { type: string; data?: any; [key: string]: any };

interface UseWebSocketOptions {
  url: string;
  onEvent?: (event: WSEvent) => void;
  enabled?: boolean;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  lastEvent: WSEvent | null;
  lastPong: number | null;
  subscribe: (channels: string[]) => void;
  unsubscribe: (channels: string[]) => void;
  send: (data: any) => void;
}

export function useWebSocket({
  url,
  onEvent,
  enabled = true,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const [lastPong, setLastPong] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number>(0);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!enabled) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    const wsUrl = `${url}${url.includes("?") ? "&" : "?"}token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          setLastPong(data.ts);
          return;
        }
        setLastEvent(data);
        onEventRef.current?.(data);
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      // Auto-reconnect with exponential backoff
      const delay = Math.min(1000 * Math.pow(2, reconnectRef.current), 30000);
      reconnectRef.current++;
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url, enabled]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const subscribe = useCallback((channels: string[]) => {
    wsRef.current?.send(JSON.stringify({ type: "subscribe", channels }));
  }, []);

  const unsubscribe = useCallback((channels: string[]) => {
    wsRef.current?.send(JSON.stringify({ type: "unsubscribe", channels }));
  }, []);

  const send = useCallback((data: any) => {
    wsRef.current?.send(JSON.stringify(data));
  }, []);

  return { isConnected, lastEvent, lastPong, subscribe, unsubscribe, send };
}
