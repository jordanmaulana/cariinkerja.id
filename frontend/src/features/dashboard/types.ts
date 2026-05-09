import type { AssessmentStatus } from "@/features/assessments/types";

export type DashboardStats = {
  assessments: {
    total: number;
    today: number;
    avg_score: number;
    by_status: Record<AssessmentStatus, number>;
  };
  preferences: {
    total: number;
    active_crawls: number;
  };
  jobs_assessed: number;
  score_buckets: [number, number, number, number];
  trend_30d: { date: string; count: number }[];
};
