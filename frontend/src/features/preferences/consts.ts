import type { PreferenceStatus } from "@/features/preferences/types";

export const PREFERENCE_STATUSES: { value: PreferenceStatus; label: string }[] = [
  { value: "waiting_payment", label: "Menunggu pembayaran" },
  { value: "waiting_admin", label: "Lagi ngumpulin loker yang kamu cari" },
  { value: "running", label: "Berjalan" },
  { value: "expired", label: "Kedaluwarsa" },
];

export const STATUS_LABEL = Object.fromEntries(
  PREFERENCE_STATUSES.map((s) => [s.value, s.label]),
) as Record<PreferenceStatus, string>;

export const STATUS_VARIANT: Record<
  PreferenceStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  waiting_payment: "outline",
  waiting_admin: "secondary",
  running: "default",
  expired: "destructive",
};
