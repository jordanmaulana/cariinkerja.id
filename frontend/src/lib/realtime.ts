import { useEffect } from "react";

import { getToken } from "@/lib/auth";

export type UserEvent = { event: string; [key: string]: unknown };

const API_BASE = `${import.meta.env.VITE_API_URL ?? ""}/api/v1`;

export function useUserEvents(handler: (e: UserEvent) => void) {
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const url = `${API_BASE}/subscriptions/stream/?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    es.onmessage = (m) => {
      try {
        handler(JSON.parse(m.data) as UserEvent);
      } catch {
        /* ignore malformed payloads */
      }
    };
    return () => es.close();
  }, [handler]);
}
