import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getAssessment,
  listAssessments,
  updateAssessmentStatus,
} from "@/features/assessments/api";
import type { AssessmentStatus } from "@/features/assessments/types";

export function useAssessment(id: string) {
  return useQuery({
    queryKey: ["assessment", id],
    queryFn: () => getAssessment(id),
  });
}

export function useAssessmentsList(params: {
  statuses: AssessmentStatus[];
  minScore: number | undefined;
  page: number;
  pageSize: number;
}) {
  const { statuses, minScore, page, pageSize } = params;
  return useQuery({
    queryKey: ["assessments", { statuses, minScore: minScore ?? null, page }],
    queryFn: () =>
      listAssessments({
        statuses: statuses.length ? statuses : undefined,
        minScore,
        page,
        pageSize,
      }),
  });
}

export function useUpdateAssessmentStatusListMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, next }: { id: string; next: AssessmentStatus }) =>
      updateAssessmentStatus(id, next),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assessments"] });
    },
  });
}

export function useUpdateAssessmentStatusDetailMutation(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (next: AssessmentStatus) => updateAssessmentStatus(id, next),
    onSuccess: (data) => {
      queryClient.setQueryData(["assessment", id], data);
      queryClient.invalidateQueries({ queryKey: ["assessments"] });
    },
  });
}
