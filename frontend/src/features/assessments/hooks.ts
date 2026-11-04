import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  getAssessment,
  listAssessments,
  updateAssessmentStatus,
} from "@/features/assessments/api";
import type { AssessmentStatus } from "@/features/assessments/types";
import type { JobType, RemoteOption } from "@/features/jobs/consts";

export function useAssessment(id: string) {
  return useQuery({
    queryKey: ["assessment", id],
    queryFn: () => getAssessment(id),
  });
}

export function useAssessmentsList(params: {
  statuses: AssessmentStatus[];
  jobTypes: JobType[];
  remoteOptions: RemoteOption[];
  minScore: number | undefined;
  q: string;
  preference: string | undefined;
  page: number;
  pageSize: number;
}) {
  const {
    statuses,
    jobTypes,
    remoteOptions,
    minScore,
    q,
    preference,
    page,
    pageSize,
  } = params;
  return useQuery({
    queryKey: [
      "assessments",
      {
        statuses,
        jobTypes,
        remoteOptions,
        minScore: minScore ?? null,
        q,
        preference: preference ?? null,
        page,
      },
    ],
    queryFn: () =>
      listAssessments({
        statuses: statuses.length ? statuses : undefined,
        jobTypes,
        remoteOptions,
        minScore,
        q: q || undefined,
        preference,
        page,
        pageSize,
      }),
    placeholderData: keepPreviousData,
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
