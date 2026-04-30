import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from "recharts"

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
import { listAssessments, type AssessmentStatus } from "@/lib/assessments"
import { getDashboardStats, type DashboardStats } from "@/lib/dashboard"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
})

const STATUS_ORDER: AssessmentStatus[] = [
  "new",
  "seen",
  "applied",
  "accepted",
  "rejected",
]

const STATUS_LABEL: Record<AssessmentStatus, string> = {
  new: "New",
  seen: "Seen",
  applied: "Applied",
  rejected: "Rejected",
  accepted: "Accepted",
}

const BUCKET_LABELS = ["0–25", "26–50", "51–75", "76–100"] as const

function DashboardPage() {
  const stats = useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: getDashboardStats,
    staleTime: 60_000,
  })
  const recent = useQuery({
    queryKey: ["dashboard", "recent"],
    queryFn: () => listAssessments(),
    staleTime: 30_000,
    select: (rows) => rows.slice(0, 5),
  })

  if (stats.isLoading) {
    return <DashboardSkeleton />
  }
  if (stats.isError || !stats.data) {
    return (
      <div className="rounded-lg border bg-card p-6 text-sm text-destructive">
        Failed to load dashboard. Refresh to try again.
      </div>
    )
  }

  const data = stats.data
  const isEmpty = data.assessments.total === 0

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Overview</h2>
        <p className="text-sm text-muted-foreground">
          Snapshot of your job-match activity. Updated on each visit.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Available Jobs"
          value={data.assessments.total}
          hint={
            data.assessments.today > 0
              ? `+${data.assessments.today} today`
              : "No new today"
          }
        />
        <StatCard
          label="Average score"
          value={data.assessments.avg_score || 0}
          suffix={data.assessments.total > 0 ? "/100" : ""}
        />
        <StatCard
          label="Active Finders"
          value={data.preferences.active_crawls}
          hint={`${data.preferences.total} total`}
        />
        <StatCard label="Jobs assessed" value={data.jobs_assessed} />
      </div>

      {isEmpty ? (
        <EmptyState />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Activity</CardTitle>
                <CardDescription>Last 30 days</CardDescription>
              </CardHeader>
              <CardContent>
                <TrendChart data={data.trend_30d} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>By status</CardTitle>
                <CardDescription>
                  Distribution across your pipeline
                </CardDescription>
              </CardHeader>
              <CardContent>
                <StatusBreakdown
                  byStatus={data.assessments.by_status}
                  total={data.assessments.total}
                />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Score distribution</CardTitle>
              <CardDescription>
                How your matches score against requirements
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScoreDistribution buckets={data.score_buckets} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <div className="space-y-1">
                <CardTitle>Recent available jobs</CardTitle>
                <CardDescription>Latest 5</CardDescription>
              </div>
              <Button asChild size="sm" variant="outline">
                <Link to="/assessments">View all</Link>
              </Button>
            </CardHeader>
            <CardContent className="px-0">
              <RecentList rows={recent.data ?? []} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  hint,
  suffix,
}: {
  label: string
  value: number
  hint?: string
  suffix?: string
}) {
  return (
    <Card>
      <CardContent className="px-5 py-4">
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className="mt-1 flex items-baseline gap-1">
          <span className="text-3xl font-semibold tabular-nums">{value}</span>
          {suffix && (
            <span className="text-sm text-muted-foreground">{suffix}</span>
          )}
        </div>
        {hint && (
          <div className="mt-1 text-xs text-muted-foreground">{hint}</div>
        )}
      </CardContent>
    </Card>
  )
}

function TrendChart({ data }: { data: DashboardStats["trend_30d"] }) {
  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            interval={Math.max(0, Math.floor(data.length / 6) - 1)}
            tickFormatter={(d: string) => {
              const date = new Date(d)
              return `${date.getMonth() + 1}/${date.getDate()}`
            }}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          />
          <Tooltip
            cursor={{ stroke: "var(--border)" }}
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
              color: "var(--foreground)",
            }}
            labelFormatter={(d) =>
              typeof d === "string"
                ? new Date(d).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })
                : ""
            }
          />
          <Line
            type="monotone"
            dataKey="count"
            stroke="var(--foreground)"
            strokeWidth={1.75}
            dot={false}
            activeDot={{ r: 3 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function StatusBreakdown({
  byStatus,
  total,
}: {
  byStatus: Record<AssessmentStatus, number>
  total: number
}) {
  return (
    <ul className="space-y-3">
      {STATUS_ORDER.map((s) => {
        const count = byStatus[s] ?? 0
        const pct = total === 0 ? 0 : Math.round((count / total) * 100)
        return (
          <li key={s} className="space-y-1.5">
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted-foreground">{STATUS_LABEL[s]}</span>
              <span className="tabular-nums">
                {count}
                <span className="ml-2 text-xs text-muted-foreground">
                  {pct}%
                </span>
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-foreground/80"
                style={{ width: `${pct}%` }}
              />
            </div>
          </li>
        )
      })}
    </ul>
  )
}

function ScoreDistribution({ buckets }: { buckets: [number, number, number, number] }) {
  const total = buckets.reduce((a, b) => a + b, 0)
  const tones = [
    "bg-foreground/15",
    "bg-foreground/35",
    "bg-foreground/60",
    "bg-foreground/85",
  ]
  return (
    <div className="space-y-3">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
        {buckets.map((count, i) => {
          const pct = total === 0 ? 0 : (count / total) * 100
          if (pct === 0) return null
          return (
            <div
              key={i}
              className={cn("h-full", tones[i])}
              style={{ width: `${pct}%` }}
              title={`${BUCKET_LABELS[i]}: ${count}`}
            />
          )
        })}
      </div>
      <ul className="grid grid-cols-2 gap-y-2 text-sm sm:grid-cols-4">
        {buckets.map((count, i) => (
          <li key={i} className="flex items-center gap-2">
            <span className={cn("size-2.5 rounded-sm", tones[i])} />
            <span className="text-muted-foreground">{BUCKET_LABELS[i]}</span>
            <span className="tabular-nums">{count}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function RecentList({
  rows,
}: {
  rows: import("@/lib/assessments").Assessment[]
}) {
  if (rows.length === 0) {
    return (
      <div className="px-6 py-4 text-sm text-muted-foreground">
        No assessments yet.
      </div>
    )
  }
  return (
    <ul className="divide-y">
      {rows.map((row) => (
        <li key={row.id}>
          <Link
            to="/assessments/$id"
            params={{ id: row.id }}
            className="flex items-center justify-between gap-4 px-6 py-3 transition-colors hover:bg-muted/50"
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">
                {row.job.title}
              </div>
              <div className="truncate text-xs text-muted-foreground">
                {row.job.company || "—"}
                {row.job.location ? ` · ${row.job.location}` : ""}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span className="text-sm tabular-nums">{row.score}</span>
              <Badge variant="outline" className="capitalize">
                {row.status}
              </Badge>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-start gap-3 py-10">
        <div>
          <h3 className="text-base font-semibold">No assessments yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Add a Finder to start crawling jobs and generating matches.
          </p>
        </div>
        <Button asChild size="sm">
          <Link to="/preferences">Manage Finders</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-64" />
      <Skeleton className="h-48" />
    </div>
  )
}
