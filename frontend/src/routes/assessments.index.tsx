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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
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

type TabValue = "all" | AssessmentStatus

const TAB_LABELS: Record<TabValue, string> = {
  all: "All",
  new: "New",
  seen: "Seen",
  applied: "Applied",
  rejected: "Rejected",
  accepted: "Accepted",
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

function AssessmentsPage() {
  const [tab, setTab] = useState<TabValue>("all")
  const [minScoreInput, setMinScoreInput] = useState("")
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const statusFilter = tab === "all" ? undefined : tab
  const parsed = minScoreInput === "" ? undefined : Number(minScoreInput)
  const minScore =
    parsed != null && Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined

  const query = useQuery({
    queryKey: ["assessments", tab, minScore ?? null],
    queryFn: () => listAssessments({ status: statusFilter, minScore }),
  })

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
        <h2 className="text-2xl font-semibold tracking-tight">Assessments</h2>
        <p className="text-sm text-muted-foreground">
          Jobs matched to your preferences. Triage the pipeline.
        </p>
      </div>

      <Card>
        <CardHeader className="flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>
              {query.data?.length ?? 0} matching{" "}
              {(query.data?.length ?? 0) === 1 ? "assessment" : "assessments"}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Tabs value={tab} onValueChange={(v) => setTab(v as TabValue)}>
              <TabsList>
                <TabsTrigger value="all">{TAB_LABELS.all}</TabsTrigger>
                {ASSESSMENT_STATUSES.map((s) => (
                  <TabsTrigger key={s} value={s}>
                    {TAB_LABELS[s]}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="number"
                min={0}
                max={100}
                inputMode="numeric"
                placeholder="Min score"
                value={minScoreInput}
                onChange={(e) => setMinScoreInput(e.target.value)}
                className="h-8 w-32 pl-7 text-xs"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-0">
          {query.isLoading && (
            <div className="px-6 pb-6">
              <Skeleton className="h-32 w-full" />
            </div>
          )}
          {query.isError && (
            <p className="px-6 pb-6 text-sm text-destructive">
              Failed to load assessments.
            </p>
          )}
          {query.data && query.data.length === 0 && !query.isLoading && (
            <p className="px-6 pb-6 text-sm text-muted-foreground">
              No assessments match these filters.
            </p>
          )}
          {query.data && query.data.length > 0 && (
            <AssessmentsTable
              rows={query.data}
              isPending={mutation.isPending}
              pendingId={mutation.variables?.id}
              onAction={(id, next) => mutation.mutate({ id, next })}
              onOpen={(id) => navigate({ to: "/assessments/$id", params: { id } })}
            />
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
              <TableCell className="max-w-[260px]">
                <span className="truncate font-medium hover:underline">
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
                <Badge variant={STATUS_VARIANT[row.status]} className="capitalize">
                  {row.status}
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
                  <span className="text-xs text-muted-foreground">—</span>
                )}
                {actions.map((a) => (
                  <Button
                    key={a.next}
                    size="xs"
                    variant={a.variant ?? "default"}
                    disabled={rowPending}
                    onClick={() => onAction(row.id, a.next)}
                  >
                    {a.label}
                  </Button>
                ))}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
