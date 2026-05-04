import { useState } from "react"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Search } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  type Assessment,
  type AssessmentStatus,
  ASSESSMENT_STATUSES,
  listAssessments,
  updateAssessmentStatus,
} from "@/lib/assessments"
import { JOB_TYPES, REMOTE_OPTIONS } from "@/lib/consts"

export const Route = createFileRoute("/assessments/")({
  component: AssessmentsPage,
})

const STATUS_LABEL: Record<AssessmentStatus, string> = {
  new: "New",
  seen: "I've reviewed",
  applied: "I applied",
  rejected: "Not interested",
  accepted: "Got an offer",
}

const STATUS_HINT: Record<AssessmentStatus, string> = {
  new: "Hasn't been reviewed yet.",
  seen: "You've looked at it but haven't applied.",
  applied: "You sent in an application.",
  rejected: "You decided not to pursue this one.",
  accepted: "Employer extended an offer.",
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
  confirm?: { title: string; description: string; confirmLabel: string }
}

const REJECT_CONFIRM = {
  title: "Reject this match?",
  description:
    "Once rejected, this job will be hidden from your queue and the action can only be reversed by support. Are you sure?",
  confirmLabel: "Yes, reject",
}

function getActionsForStatus(status: AssessmentStatus): Action[] {
  switch (status) {
    case "new":
      return [
        { label: "Mark reviewed", next: "seen", variant: "outline" },
        {
          label: "Reject",
          next: "rejected",
          variant: "destructive",
          confirm: REJECT_CONFIRM,
        },
      ]
    case "seen":
      return [
        { label: "I applied", next: "applied", variant: "default" },
        {
          label: "Reject",
          next: "rejected",
          variant: "destructive",
          confirm: REJECT_CONFIRM,
        },
      ]
    case "applied":
      return [
        { label: "Got an offer", next: "accepted", variant: "default" },
        {
          label: "Reject",
          next: "rejected",
          variant: "destructive",
          confirm: REJECT_CONFIRM,
        },
      ]
    default:
      return []
  }
}

const PAGE_SIZE = 10

function AssessmentsPage() {
  const [selectedStatuses, setSelectedStatuses] = useState<
    Set<AssessmentStatus>
  >(() => new Set(["new"]))
  const [minScoreInput, setMinScoreInput] = useState("80")
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const parsed = minScoreInput === "" ? undefined : Number(minScoreInput)
  const minScore =
    parsed != null && Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined

  const statuses = [...selectedStatuses].sort()

  const query = useQuery({
    queryKey: ["assessments", { statuses, minScore: minScore ?? null, page }],
    queryFn: () =>
      listAssessments({
        statuses: statuses.length ? statuses : undefined,
        minScore,
        page,
        pageSize: PAGE_SIZE,
      }),
  })

  const rows = query.data?.results
  const count = query.data?.count ?? 0
  const numPages = query.data?.num_pages ?? 1

  function toggleStatus(s: AssessmentStatus, checked: boolean) {
    setSelectedStatuses((prev) => {
      const next = new Set(prev)
      if (checked) next.add(s)
      else next.delete(s)
      return next
    })
    setPage(1)
  }

  function handleMinScoreChange(value: string) {
    setMinScoreInput(value)
    setPage(1)
  }

  const mutation = useMutation({
    mutationFn: ({ id, next }: { id: string; next: AssessmentStatus }) =>
      updateAssessmentStatus(id, next),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assessments"] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Available Jobs</h2>
        <p className="text-sm text-muted-foreground">
          Jobs matched to your Finders. Mark each as you go so we can track your
          progress.
        </p>
      </div>

      <Card>
        <CardHeader className="flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>
              {count} matching{" "}
              {count === 1 ? "available job" : "available jobs"}
              {numPages > 1 && ` · Page ${page} of ${numPages}`}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex flex-wrap items-center gap-3">
              {ASSESSMENT_STATUSES.map((s) => (
                <label
                  key={s}
                  className="flex cursor-pointer items-center gap-2 text-sm"
                  title={STATUS_HINT[s]}
                >
                  <Checkbox
                    checked={selectedStatuses.has(s)}
                    onCheckedChange={(c) => toggleStatus(s, c === true)}
                  />
                  {STATUS_LABEL[s]}
                </label>
              ))}
            </div>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="number"
                min={0}
                max={100}
                inputMode="numeric"
                placeholder="Min score"
                title="LLM match score, 0–100"
                value={minScoreInput}
                onChange={(e) => handleMinScoreChange(e.target.value)}
                className="h-8 w-32 pl-7 text-xs"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-0">
          <p className="px-6 pb-3 text-xs text-muted-foreground">
            Statuses: {ASSESSMENT_STATUSES.map((s) => STATUS_LABEL[s]).join(" · ")}
          </p>
          {query.isLoading && (
            <div className="px-6 pb-6">
              <Skeleton className="h-32 w-full" />
            </div>
          )}
          {query.isError && (
            <p className="px-6 pb-6 text-sm text-destructive">
              Failed to load available jobs.
            </p>
          )}
          {rows && rows.length === 0 && !query.isLoading && (
            <p className="px-6 pb-6 text-sm text-muted-foreground">
              No available jobs match these filters.
            </p>
          )}
          {rows && rows.length > 0 && (
            <AssessmentsTable
              rows={rows}
              isPending={mutation.isPending}
              pendingId={mutation.variables?.id}
              onAction={(id, next) => mutation.mutate({ id, next })}
              onOpen={(id) => navigate({ to: "/assessments/$id", params: { id } })}
            />
          )}
          {count > 0 && (
            <div className="flex items-center justify-between gap-3 px-6 pb-6 pt-4">
              <span className="text-xs text-muted-foreground">
                Page {page} of {numPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1 || query.isFetching}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= numPages || query.isFetching}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function AssessmentsTable({
  rows,
  isPending,
  pendingId,
  onAction,
  onOpen,
}: {
  rows: Assessment[]
  isPending: boolean
  pendingId?: string
  onAction: (id: string, next: AssessmentStatus) => void
  onOpen: (id: string) => void
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Job</TableHead>
          <TableHead>Company</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Remote</TableHead>
          <TableHead className="text-right">Score</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Assessed</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => {
          const actions = getActionsForStatus(row.status)
          const rowPending = isPending && pendingId === row.id
          const created = new Date(row.created_on).toLocaleDateString()
          return (
            <TableRow
              key={row.id}
              className="cursor-pointer"
              onClick={() => onOpen(row.id)}
            >
              <TableCell className="max-w-[280px]">
                <span
                  className="block truncate font-medium hover:underline"
                  title={row.job.title}
                >
                  {row.job.title}
                </span>
              </TableCell>
              <TableCell>
                <div className="font-medium">{row.job.company ?? "—"}</div>
                {row.job.location && (
                  <div className="text-xs text-muted-foreground">
                    {row.job.location}
                  </div>
                )}
              </TableCell>
              <TableCell>
                {row.job.job_type ? JOB_TYPE_LABEL[row.job.job_type] : "—"}
              </TableCell>
              <TableCell>
                {row.job.remote_option
                  ? REMOTE_LABEL[row.job.remote_option]
                  : "—"}
              </TableCell>
              <TableCell className="text-right font-medium tabular-nums">
                {row.score}
              </TableCell>
              <TableCell>
                <Badge
                  variant={STATUS_VARIANT[row.status]}
                  title={STATUS_HINT[row.status]}
                >
                  {STATUS_LABEL[row.status]}
                </Badge>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {created}
              </TableCell>
              <TableCell
                className="space-x-1.5 text-right"
                onClick={(e) => e.stopPropagation()}
              >
                {actions.length === 0 && (
                  <span
                    className="text-xs text-muted-foreground"
                    title="Final status — no further actions."
                  >
                    —
                  </span>
                )}
                {actions.map((a) =>
                  a.confirm ? (
                    <ConfirmActionButton
                      key={a.next}
                      action={a}
                      disabled={rowPending}
                      onConfirm={() => onAction(row.id, a.next)}
                    />
                  ) : (
                    <Button
                      key={a.next}
                      size="xs"
                      variant={a.variant ?? "default"}
                      disabled={rowPending}
                      onClick={() => onAction(row.id, a.next)}
                    >
                      {a.label}
                    </Button>
                  ),
                )}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

function ConfirmActionButton({
  action,
  disabled,
  onConfirm,
}: {
  action: Action
  disabled: boolean
  onConfirm: () => void
}) {
  const [open, setOpen] = useState(false)
  if (!action.confirm) return null
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button
        size="xs"
        variant={action.variant ?? "default"}
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        {action.label}
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{action.confirm.title}</DialogTitle>
          <DialogDescription>{action.confirm.description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </DialogClose>
          <Button
            type="button"
            variant={action.variant ?? "default"}
            onClick={() => {
              setOpen(false)
              onConfirm()
            }}
          >
            {action.confirm.confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
