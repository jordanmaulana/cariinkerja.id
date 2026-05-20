import { api } from "@/lib/api";

export type PublicStatBucket = { total: number; today: number };

export type PublicStats = {
  profiles: PublicStatBucket;
  jobs: PublicStatBucket;
  assessments: PublicStatBucket;
  highly_suitable: PublicStatBucket;
};

export function getPublicStats(): Promise<PublicStats> {
  return api<PublicStats>("/landing/stats/", { skipAuth: true });
}
