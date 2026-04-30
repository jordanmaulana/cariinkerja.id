import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  type Assessment,
  type AssessmentStatus,
  getAssessment,
  updateAssessmentStatus,
} from "@/lib/assessments";
import { JOB_TYPES, REMOTE_OPTIONS } from "@/lib/consts";

export const Route = createFileRoute("/assessments/$id")({
  component: AssessmentDetailPage,
});

const STATUS_VARIANT: Record<
  AssessmentStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  new: "secondary",
  seen: "outline",
  applied: "default",
  rejected: "destructive",
  accepted: "default",
};

const JOB_TYPE_LABEL = Object.fromEntries(
  JOB_TYPES.map((j) => [j.value, j.label]),
);
const REMOTE_LABEL = Object.fromEntries(
  REMOTE_OPTIONS.map((r) => [r.value, r.label]),
);

type Action = {
  label: string;
  next: AssessmentStatus;
  variant?: "default" | "destructive" | "outline";
};

function getActionsForStatus(status: AssessmentStatus): Action[] {
  switch (status) {
    case "new":
      return [
        { label: "Mark Seen", next: "seen", variant: "outline" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ];
    case "seen":
      return [
        { label: "Mark Applied", next: "applied", variant: "default" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ];
    case "applied":
      return [
        { label: "Mark Accepted", next: "accepted", variant: "default" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ];
    default:
      return [];
  }
}

function AssessmentDetailPage() {
  const { id } = Route.useParams();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["assessment", id],
    queryFn: () => getAssessment(id),
  });

  const mutation = useMutation({
    mutationFn: (next: AssessmentStatus) => updateAssessmentStatus(id, next),
    onSuccess: (data) => {
      queryClient.setQueryData(["assessment", id], data);
      queryClient.invalidateQueries({ queryKey: ["assessments"] });
    },
  });

  return (
    <main className="p-8 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <Link
          to="/assessments"
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Back to assessments
        </Link>
      </div>

      {query.isLoading && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}
      {query.isError && (
        <p className="text-sm text-destructive">
          Failed to load assessment. It may not exist or you may not have access.
        </p>
      )}

      {query.data && (
        <AssessmentDetail
          assessment={query.data}
          isPending={mutation.isPending}
          onAction={(next) => mutation.mutate(next)}
        />
      )}
    </main>
  );
}

function AssessmentDetail({
  assessment,
  isPending,
  onAction,
}: {
  assessment: Assessment;
  isPending: boolean;
  onAction: (next: AssessmentStatus) => void;
}) {
  const { job, preference, status, score, verdict, created_on } = assessment;
  const actions = getActionsForStatus(status);
  const created = new Date(created_on).toLocaleDateString();

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">{job.title}</h1>
            <p className="text-sm font-medium">{job.company ?? "—"}</p>
            <p className="text-sm text-muted-foreground">
              {job.location ?? "—"} ·{" "}
              {job.job_type ? JOB_TYPE_LABEL[job.job_type] : "—"} ·{" "}
              {job.remote_option ? REMOTE_LABEL[job.remote_option] : "—"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              For preference:{" "}
              <span className="font-medium">{preference.title ?? "—"}</span> ·
              Assessed {created}
            </p>
          </div>
          <Badge variant={STATUS_VARIANT[status]}>{status}</Badge>
        </div>
        <a
          href={job.url}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-primary hover:underline"
        >
          View original posting →
        </a>
      </div>

      <div className="rounded-lg border p-4 flex items-center gap-6">
        <div>
          <p className="text-xs text-muted-foreground">Match score</p>
          <p className="text-3xl font-bold">{score}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {actions.length === 0 ? (
            <span className="text-sm text-muted-foreground">
              Terminal status — no further actions.
            </span>
          ) : (
            actions.map((a) => (
              <Button
                key={a.next}
                variant={a.variant ?? "default"}
                disabled={isPending}
                onClick={() => onAction(a.next)}
              >
                {a.label}
              </Button>
            ))
          )}
        </div>
      </div>

      {verdict && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Verdict
          </h2>
          <p className="text-sm whitespace-pre-line">{verdict}</p>
        </section>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <SkillList title="Hard skill match" items={assessment.hard_skill_match} />
        <SkillList
          title="Hard skill gap"
          items={assessment.hard_skill_gap}
          tone="gap"
        />
        <SkillList title="Soft skill match" items={assessment.soft_skill_match} />
        <SkillList
          title="Soft skill gap"
          items={assessment.soft_skill_gap}
          tone="gap"
        />
      </div>
    </div>
  );
}

function SkillList({
  title,
  items,
  tone = "match",
}: {
  title: string;
  items: string[];
  tone?: "match" | "gap";
}) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        {title}
      </h2>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">None.</p>
      ) : (
        <ul className="flex flex-wrap gap-1.5">
          {items.map((s, i) => (
            <li key={`${s}-${i}`}>
              <Badge variant={tone === "gap" ? "destructive" : "secondary"}>
                {s}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
