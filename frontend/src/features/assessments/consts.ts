import type { AssessmentStatus } from "@/features/assessments/types";

export const ASSESSMENT_STATUSES: AssessmentStatus[] = [
  "new",
  "seen",
  "applied",
  "rejected",
  "accepted",
];

export const STATUS_ORDER: AssessmentStatus[] = [
  "new",
  "seen",
  "applied",
  "accepted",
  "rejected",
];

export const STATUS_LABEL: Record<AssessmentStatus, string> = {
  new: "Baru",
  seen: "Sudah dilihat",
  applied: "Sudah dilamar",
  rejected: "Ditolak",
  accepted: "Dapat tawaran",
};

export const STATUS_HINT: Record<AssessmentStatus, string> = {
  new: "Belum dilihat.",
  seen: "Sudah kamu lihat tapi belum dilamar.",
  applied: "Kamu sudah kirim lamaran.",
  rejected: "Kamu memutuskan untuk tidak ngelanjutin loker ini.",
  accepted: "Perusahaan ngasih tawaran.",
};

export const STATUS_VARIANT: Record<
  AssessmentStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  new: "secondary",
  seen: "outline",
  applied: "default",
  rejected: "destructive",
  accepted: "default",
};
