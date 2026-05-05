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
