import type { JobType, RemoteOption } from "@/features/jobs/consts";
import type {
  Preference,
  PreferencePayload,
} from "@/features/preferences/types";

export function arraysEqual<T>(a: T[], b: T[]): boolean {
  if (a.length !== b.length) return false;
  const sortedA = [...a].sort();
  const sortedB = [...b].sort();
  return sortedA.every((v, i) => v === sortedB[i]);
}

export type PreferenceFormValues = {
  title: string;
  job_type: JobType[];
  remote_option: RemoteOption[];
};

export function buildInitialValues(p?: Preference | null): PreferenceFormValues {
  return {
    title: p?.title ?? "",
    job_type: p?.job_type ?? [],
    remote_option: p?.remote_option ?? [],
  };
}

export function valuesToPayload(v: PreferenceFormValues): PreferencePayload {
  return {
    title: v.title.trim() || null,
    job_type: v.job_type,
    remote_option: v.remote_option,
  };
}
