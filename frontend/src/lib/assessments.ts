import { api } from "@/lib/api";
import type { JobType, RemoteOption } from "@/lib/consts";

export type AssessmentStatus =
  | "new"
  | "seen"
  | "applied"
  | "rejected"
  | "accepted";

export type AssessmentJob = {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  url: string;
  job_type: JobType | null;
  remote_option: RemoteOption | null;
};

export type AssessmentPreference = {
  id: string;
  title: string | null;
};

export type Assessment = {
  id: string;
  status: AssessmentStatus;
  score: number;
  verdict: string | null;
  created_on: string;
  job: AssessmentJob;
  preference: AssessmentPreference;
  soft_skill_match: string[];
  soft_skill_gap: string[];
  hard_skill_match: string[];
  hard_skill_gap: string[];
};

export const ASSESSMENT_STATUSES: AssessmentStatus[] = [
  "new",
  "seen",
  "applied",
  "rejected",
  "accepted",
];

export type AssessmentListParams = {
  statuses?: AssessmentStatus[];
  minScore?: number;
  page?: number;
  pageSize?: number;
};

export type AssessmentListPage = {
  count: number;
  page: number;
  page_size: number;
  num_pages: number;
  results: Assessment[];
};

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
