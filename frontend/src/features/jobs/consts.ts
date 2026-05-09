export const JOB_TYPES = [
  { value: "full-time", label: "Penuh waktu" },
  { value: "part-time", label: "Paruh waktu" },
  { value: "contract", label: "Kontrak" },
  { value: "internship", label: "Magang" },
] as const;

export type JobType = (typeof JOB_TYPES)[number]["value"];

export const REMOTE_OPTIONS = [
  { value: "remote", label: "Remote" },
  { value: "on-site", label: "On-site" },
  { value: "hybrid", label: "Hybrid" },
] as const;

export type RemoteOption = (typeof REMOTE_OPTIONS)[number]["value"];

export const JOB_TYPE_LABEL: Record<JobType, string> = Object.fromEntries(
  JOB_TYPES.map((j) => [j.value, j.label]),
) as Record<JobType, string>;

export const REMOTE_LABEL: Record<RemoteOption, string> = Object.fromEntries(
  REMOTE_OPTIONS.map((r) => [r.value, r.label]),
) as Record<RemoteOption, string>;
