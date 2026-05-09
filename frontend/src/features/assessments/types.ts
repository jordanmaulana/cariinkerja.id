import type { JobType, RemoteOption } from "@/features/jobs/consts";

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
