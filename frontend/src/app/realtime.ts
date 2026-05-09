import { useCallback, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "react-toastify";

import { getToken } from "@/features/auth/api";

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

function describeEvent(e: UserEvent): string | null {
  switch (e.event) {
    case "subscription.activated":
      return "Langganan aktif. Pencocokan harian sudah jalan.";
    case "preference.status_changed": {
      const status = typeof e.status === "string" ? e.status : null;
      const label =
        status === "running"
          ? "berjalan"
          : status === "waiting_payment"
            ? "disetujui — pilih paket"
            : status === "waiting_admin"
              ? "kembali ditinjau admin"
              : status === "expired"
                ? "kedaluwarsa"
                : status;
      return label ? `Status Pencarian: ${label}.` : "Status Pencarian diperbarui.";
    }
    case "assessment.status_changed":
      return null;
    default:
      return null;
  }
}

export function useRealtimeQueryInvalidation() {
  const queryClient = useQueryClient();
  const handler = useCallback(
    (e: UserEvent) => {
      switch (e.event) {
        case "assessment.status_changed":
          if (typeof e.assessment_id === "string") {
            queryClient.invalidateQueries({
              queryKey: ["assessment", e.assessment_id],
            });
          }
          queryClient.invalidateQueries({ queryKey: ["assessments"] });
          break;
        case "subscription.activated":
          queryClient.invalidateQueries({ queryKey: ["subscription", "me"] });
          queryClient.invalidateQueries({ queryKey: ["plans"] });
          queryClient.invalidateQueries({ queryKey: ["payment-gate"] });
          break;
        case "preference.status_changed":
          queryClient.invalidateQueries({ queryKey: ["preferences"] });
          if (typeof e.preference_id === "string") {
            queryClient.invalidateQueries({
              queryKey: ["preference", e.preference_id],
            });
          }
          queryClient.invalidateQueries({ queryKey: ["payment-gate"] });
          break;
      }
      const msg = describeEvent(e);
      if (msg) {
        if (e.event === "subscription.activated") toast.success(msg);
        else toast.info(msg);
      }
    },
    [queryClient],
  );
  useUserEvents(handler);
}
