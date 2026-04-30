import { Link, createFileRoute } from "@tanstack/react-router"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, ExternalLink } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  type Assessment,
  type AssessmentStatus,
  getAssessment,
  updateAssessmentStatus,
} from "@/lib/assessments"
import { JOB_TYPES, REMOTE_OPTIONS } from "@/lib/consts"

export const Route = createFileRoute("/assessments/$id")({
  component: AssessmentDetailPage,
})

const STATUS_VARIANT: Record<
  AssessmentStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  new: "secondary",
  seen: "outline",
  applied: "default",
  rejected: "destructive",
  accepted: "default",
}

const JOB_TYPE_LABEL = Object.fromEntries(
  JOB_TYPES.map((j) => [j.value, j.label]),
)
const REMOTE_LABEL = Object.fromEntries(
  REMOTE_OPTIONS.map((r) => [r.value, r.label]),
)

type Action = {
  label: string
  next: AssessmentStatus
  variant?: "default" | "destructive" | "outline"
}

function getActionsForStatus(status: AssessmentStatus): Action[] {
  switch (status) {
    case "new":
      return [
        { label: "Mark seen", next: "seen", variant: "outline" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ]
    case "seen":
      return [
        { label: "Mark applied", next: "applied", variant: "default" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ]
    case "applied":
      return [
        { label: "Mark accepted", next: "accepted", variant: "default" },
        { label: "Reject", next: "rejected", variant: "destructive" },
      ]
    default:
      return []
  }
}

function AssessmentDetailPage() {
  const { id } = Route.useParams()
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ["assessment", id],
    queryFn: () => getAssessment(id),
  })

  const mutation = useMutation({
    mutationFn: (next: AssessmentStatus) => updateAssessmentStatus(id, next),
    onSuccess: (data) => {
      queryClient.setQueryData(["assessment", id], data)
      queryClient.invalidateQueries({ queryKey: ["assessments"] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/assessments">
            <ArrowLeft className="size-4" />
            Back to available jobs
          </Link>
        </Button>
        {query.data && (
          <Badge variant={STATUS_VARIANT[query.data.status]} className="capitalize">
            {query.data.status}
          </Badge>
        )}
      </div>

      {query.isLoading && <Skeleton className="h-96 w-full" />}
      {query.isError && (
        <Card>
          <CardContent className="py-6 text-sm text-destructive">
            Failed to load available job. It may not exist or you may not have access.
          </CardContent>
        </Card>
      )}

      {query.data && (
        <AssessmentDetail
          assessment={query.data}
          isPending={mutation.isPending}
          onAction={(next) => mutation.mutate(next)}
        />
      )}
    </div>
  )
}

function AssessmentDetail({
  assessment,
  isPending,
  onAction,
}: {
  assessment: Assessment
  isPending: boolean
  onAction: (next: AssessmentStatus) => void
}) {
  const { job, preference, status, score, verdict, created_on } = assessment
  const actions = getActionsForStatus(status)
  const created = new Date(created_on).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="space-y-2">
            <CardTitle className="text-xl">{job.title}</CardTitle>
            <CardDescription>
              <span className="font-medium text-foreground">
                {job.company ?? "—"}
              </span>
              {" · "}
              {job.location ?? "—"}
              {" · "}
              {job.job_type ? JOB_TYPE_LABEL[job.job_type] : "—"}
              {" · "}
              {job.remote_option ? REMOTE_LABEL[job.remote_option] : "—"}
            </CardDescription>
            <div className="text-xs text-muted-foreground">
              Matched against{" "}
              <span className="font-medium text-foreground">
                {preference.title ?? "—"}
              </span>
              {" · Assessed "}
              {created}
            </div>
          </div>
        </CardHeader>
        <CardContent className="border-t pt-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Match score
              </div>
              <div className="mt-0.5 flex items-baseline gap-1">
                <span className="text-3xl font-semibold tabular-nums">
                  {score}
                </span>
                <span className="text-sm text-muted-foreground">/100</span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button asChild variant="outline" size="sm">
                <a href={job.url} target="_blank" rel="noreferrer">
                  <ExternalLink className="size-3.5" />
                  Original posting
                </a>
              </Button>
              {actions.length === 0 ? (
                <span className="text-xs text-muted-foreground">
                  Terminal status — no further actions.
                </span>
              ) : (
                actions.map((a) => (
                  <Button
                    key={a.next}
                    size="sm"
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
        </CardContent>
      </Card>

      {verdict && (
        <Card>
          <CardHeader>
            <CardTitle>Verdict</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm leading-relaxed">
              {verdict}
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <SkillCard title="Hard skill match" items={assessment.hard_skill_match} />
        <SkillCard
          title="Hard skill gap"
          items={assessment.hard_skill_gap}
          tone="gap"
        />
        <SkillCard title="Soft skill match" items={assessment.soft_skill_match} />
        <SkillCard
          title="Soft skill gap"
          items={assessment.soft_skill_gap}
          tone="gap"
        />
      </div>
    </div>
  )
}

function SkillCard({
  title,
  items,
  tone = "match",
}: {
  title: string
  items: string[]
  tone?: "match" | "gap"
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent>
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
      </CardContent>
    </Card>
  )
}
