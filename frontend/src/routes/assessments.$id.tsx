import { Link, createFileRoute } from "@tanstack/react-router"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Check, ExternalLink, X } from "lucide-react"

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

const STATUS_LABEL: Record<AssessmentStatus, string> = {
  new: "Baru",
  seen: "Sudah dilihat",
  applied: "Sudah dilamar",
  rejected: "Ditolak",
  accepted: "Dapat tawaran",
}

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
        { label: "Tandai sudah dilihat", next: "seen", variant: "outline" },
        { label: "Tolak", next: "rejected", variant: "destructive" },
      ]
    case "seen":
      return [
        { label: "Sudah dilamar", next: "applied", variant: "default" },
        { label: "Tolak", next: "rejected", variant: "destructive" },
      ]
    case "applied":
      return [
        { label: "Dapat tawaran", next: "accepted", variant: "default" },
        { label: "Tolak", next: "rejected", variant: "destructive" },
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
            Kembali ke loker tersedia
          </Link>
        </Button>
        {query.data && (
          <Badge variant={STATUS_VARIANT[query.data.status]}>
            {STATUS_LABEL[query.data.status]}
          </Badge>
        )}
      </div>

      {query.isLoading && <Skeleton className="h-96 w-full" />}
      {query.isError && (
        <Card>
          <CardContent className="py-6 text-sm text-destructive">
            Gagal memuat loker. Mungkin lokernya tidak ada atau kamu tidak punya akses.
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
  const created = new Date(created_on).toLocaleDateString("id-ID", {
    day: "2-digit",
    month: "short",
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
              Dicocokkan dengan{" "}
              <span className="font-medium text-foreground">
                {preference.title ?? "—"}
              </span>
              {" · Dinilai "}
              {created}
            </div>
          </div>
        </CardHeader>
        <CardContent className="border-t pt-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Skor kecocokan
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
                  Lihat loker asli
                </a>
              </Button>
              {actions.length === 0 ? (
                <span className="text-xs text-muted-foreground">
                  Status final — tidak ada aksi lebih lanjut.
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
            <CardTitle>Penilaian</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm leading-relaxed">
              {verdict}
            </p>
          </CardContent>
        </Card>
      )}

      <SkillGapCard assessment={assessment} />
    </div>
  )
}

function SkillGapCard({ assessment }: { assessment: Assessment }) {
  const groups = [
    {
      label: "Hard skill",
      match: assessment.hard_skill_match,
      gap: assessment.hard_skill_gap,
    },
    {
      label: "Soft skill",
      match: assessment.soft_skill_match,
      gap: assessment.soft_skill_gap,
    },
  ]
  return (
    <Card>
      <CardHeader>
        <CardTitle>Skill gap</CardTitle>
        <CardDescription>Apa yang udah & belum</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 sm:grid-cols-2">
        {groups.map((g) => (
          <div key={g.label}>
            <FieldLabel>{g.label}</FieldLabel>
            {g.match.length === 0 && g.gap.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">Belum ada.</p>
            ) : (
              <ul className="mt-2 space-y-1.5">
                {g.match.map((s) => (
                  <li key={`m-${s}`} className="flex items-center gap-2 text-sm">
                    <span className="grid size-5 place-items-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      <Check className="size-3" />
                    </span>
                    {s}
                  </li>
                ))}
                {g.gap.map((s) => (
                  <li
                    key={`g-${s}`}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <span className="grid size-5 place-items-center rounded-full bg-destructive/10 text-destructive">
                      <X className="size-3" />
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
      {children}
    </div>
  )
}
