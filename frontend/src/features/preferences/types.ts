import type { JobType, RemoteOption } from "@/features/jobs/consts";

export type PreferenceStatus =
  | "waiting_payment"
  | "waiting_admin"
  | "running"
  | "expired";

export type Preference = {
  id: string;
  title: string | null;
  job_type: JobType[];
  remote_option: RemoteOption[];
  crawl_urls: string[];
  status: PreferenceStatus;
  created_on: string;
  updated_on: string;
};

export type PreferencePayload = {
  title?: string | null;
  job_type?: JobType[];
  remote_option?: RemoteOption[];
};
