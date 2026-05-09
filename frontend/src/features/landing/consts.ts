import {
  Briefcase,
  Sparkles,
  Target,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

export const HERO_SCORE = 87;
export const HERO_HARD_MATCH = ["React", "TypeScript", "Tailwind"] as const;
export const HERO_HARD_GAP = ["GraphQL"] as const;

export const ASSESSMENT_MOCK = {
  job: "Frontend Engineer",
  company: "Tokopedia",
  location: "Jakarta",
  verdict:
    "Cocok banget. Stack React + TS-mu nyambung. Sentuh GraphQL dikit lagi udah aman.",
  hardMatch: ["React", "TypeScript", "Tailwind", "REST API"],
  hardGap: ["GraphQL", "Kubernetes"],
} as const;

export const SKILL_GROUPS = [
  {
    label: "Hard skill",
    match: ["React", "TypeScript", "Tailwind"],
    gap: ["GraphQL", "Kubernetes"],
  },
  {
    label: "Soft skill",
    match: ["Komunikasi", "Ownership"],
    gap: ["Public speaking"],
  },
] as const;

export const STAT_TILES: { label: string; value: string; icon: LucideIcon }[] = [
  { label: "Loker dinilai", value: "142", icon: Briefcase },
  { label: "Rata-rata skor", value: "78", icon: Target },
  { label: "Minggu ini", value: "23", icon: TrendingUp },
  { label: "Skor tertinggi", value: "94", icon: Sparkles },
];

export const BAR_CHART = [42, 58, 71, 65, 80, 73, 88];
