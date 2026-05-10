import { api } from "@/lib/api";
import type { DashboardStats } from "@/features/dashboard/types";

export async function getDashboardStats(): Promise<DashboardStats> {
  return api<DashboardStats>("/dashboard/stats/");
}
