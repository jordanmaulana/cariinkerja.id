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
  status?: AssessmentStatus;
  minScore?: number;
};

export async function listAssessments(
  params: AssessmentListParams = {},
): Promise<Assessment[]> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.minScore != null && !Number.isNaN(params.minScore))
    search.set("min_score", String(params.minScore));
  const qs = search.toString();
  return api<Assessment[]>(`/assessments/${qs ? `?${qs}` : ""}`);
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
