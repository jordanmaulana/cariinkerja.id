import type { AssessmentStatus } from "@/features/assessments/types";

export type Action = {
  label: string;
  next: AssessmentStatus;
  variant?: "default" | "destructive" | "outline";
  confirm?: { title: string; description: string; confirmLabel: string };
};

export const REJECT_CONFIRM = {
  title: "Tolak kecocokan ini?",
  description:
    "Loker ini pindah ke status Ditolak dan statusnya nggak bisa kamu ubah lagi. Kamu tetap bisa lihat lewat filter status Ditolak. Yakin?",
  confirmLabel: "Ya, tolak",
};

export function getActionsForStatus(status: AssessmentStatus): Action[] {
  switch (status) {
    case "new":
      return [
        { label: "Tandai sudah dilihat", next: "seen", variant: "outline" },
        {
          label: "Tolak",
          next: "rejected",
          variant: "destructive",
          confirm: REJECT_CONFIRM,
        },
      ];
    case "seen":
      return [
        { label: "Sudah dilamar", next: "applied", variant: "default" },
        {
          label: "Tolak",
          next: "rejected",
          variant: "destructive",
          confirm: REJECT_CONFIRM,
        },
      ];
    case "applied":
      return [
        { label: "Dapat tawaran", next: "accepted", variant: "default" },
        {
          label: "Tolak",
          next: "rejected",
          variant: "destructive",
          confirm: REJECT_CONFIRM,
        },
      ];
    default:
      return [];
  }
}
