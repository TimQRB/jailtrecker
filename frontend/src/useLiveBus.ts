// WebSocket-хук с авто-reconnect. Токен НЕ в URL — шлём первым сообщением (security-фикс).
import { useEffect, useRef, useState } from "react";
import { tokenStore } from "./api";

export interface BusMessage {
  type: string;
  payload?: Record<string, unknown>;
}

export function useLiveBus(onMessage: (m: BusMessage) => void) {
  const [connected, setConnected] = useState(false);
  const cbRef = useRef(onMessage);
  cbRef.current = onMessage;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retry = 0;
    let closed = false;
    let timer: ReturnType<typeof setTimeout>;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${window.location.host}/ws`);

      ws.onopen = () => {
        retry = 0;
        // аутентификация первым сообщением — токен не светится в query
        ws?.send(JSON.stringify({ type: "auth", token: tokenStore.get() }));
        setConnected(true);
      };
      ws.onmessage = (e) => {
        try {
          cbRef.current(JSON.parse(e.data));
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (closed) return;
        retry += 1;
        timer = setTimeout(connect, Math.min(1000 * retry, 10000));
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, []);

  return { connected };
}
