import type {
  PaymentGateCode,
  SubscriptionStatus,
} from "@/features/billing/types";

export const STATUS_LABEL: Record<SubscriptionStatus, string> = {
  PENDING: "Menunggu pembayaran",
  ACTIVE: "Aktif",
  EXPIRED: "Kedaluwarsa",
  CANCELLED: "Dibatalkan",
  REPLACED: "Diganti",
};

export const STATUS_VARIANT: Record<
  SubscriptionStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  PENDING: "secondary",
  ACTIVE: "default",
  EXPIRED: "outline",
  CANCELLED: "destructive",
  REPLACED: "outline",
};

export const GATE_REASON: Record<PaymentGateCode, string> = {
  waiting_admin:
    "LinkedIn sedang ditinjau admin — tunggu persetujuan sebelum berlangganan.",
  linkedin_quality:
    "Profil LinkedIn perlu lebih lengkap sebelum kamu bisa berlangganan.",
};

export const OPEN_TO_WORK_HINT =
  "Diskon Open-to-Work otomatis berlaku selama kamu belum punya langganan aktif. Perpanjangan tetap harga normal.";
