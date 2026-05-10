import { useQuery } from "@tanstack/react-query";

import { listAssessments } from "@/features/assessments/api";
import { getDashboardStats } from "@/features/dashboard/api";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: getDashboardStats,
    staleTime: 60_000,
  });
}

export function useRecentAssessments() {
  return useQuery({
    queryKey: ["dashboard", "recent"],
    queryFn: () => listAssessments({ pageSize: 5 }),
    staleTime: 30_000,
    select: (page) => page.results,
  });
}
