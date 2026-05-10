import { ASSESSMENT_STATUSES } from "@/features/assessments/consts";
import type { AssessmentStatus } from "@/features/assessments/types";

const ASSESSMENT_STATUS_SET = new Set<AssessmentStatus>(ASSESSMENT_STATUSES);

export function isAssessmentStatus(v: unknown): v is AssessmentStatus {
  return (
    typeof v === "string" && ASSESSMENT_STATUS_SET.has(v as AssessmentStatus)
  );
}

export function parseMinScoreInput(input: string): number | undefined {
  if (input === "") return undefined;
  const parsed = Number(input);
  if (!Number.isFinite(parsed) || parsed < 0) return undefined;
  return parsed;
}

export function sortStatuses(set: Set<AssessmentStatus>): AssessmentStatus[] {
  return [...set].sort();
}
