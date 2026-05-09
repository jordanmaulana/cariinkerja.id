import { api } from "@/lib/api";
import type {
  Assessment,
  AssessmentListPage,
  AssessmentListParams,
  AssessmentStatus,
} from "@/features/assessments/types";

export async function listAssessments(
  params: AssessmentListParams = {},
): Promise<AssessmentListPage> {
  const search = new URLSearchParams();
  if (params.statuses)
    for (const s of params.statuses) search.append("status", s);
  if (params.minScore != null && !Number.isNaN(params.minScore))
    search.set("min_score", String(params.minScore));
  if (params.page != null) search.set("page", String(params.page));
  if (params.pageSize != null)
    search.set("page_size", String(params.pageSize));
  const qs = search.toString();
  return api<AssessmentListPage>(`/assessments/${qs ? `?${qs}` : ""}`);
}

export async function getAssessment(id: string): Promise<Assessment> {
  return api<Assessment>(`/assessments/${id}/`);
}

export async function updateAssessmentStatus(
  id: string,
  status: AssessmentStatus,
): Promise<Assessment> {
  return api<Assessment>(`/assessments/${id}/`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}
