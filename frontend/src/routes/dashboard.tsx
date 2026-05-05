import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from "recharts"

import {
  PaymentGateBanner,
  usePaymentGate,
} from "@/components/payment-gate-banner"
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
import { listPreferences } from "@/lib/preferences"
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
  new: "Baru",
  seen: "Sudah dilihat",
  applied: "Sudah dilamar",
  rejected: "Ditolak",
  accepted: "Dapat tawaran",
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
    queryFn: () => listAssessments({ pageSize: 5 }),
    staleTime: 30_000,
    select: (page) => page.results,
  })
  const gate = usePaymentGate()
  const prefs = useQuery({
    queryKey: ["preferences"],
    queryFn: listPreferences,
  })
  const hasWaitingPayment =
    !gate.data?.locked &&
    !!prefs.data?.some((p) => p.status === "waiting_payment")

  if (stats.isLoading) {
    return <DashboardSkeleton />
  }
  if (stats.isError || !stats.data) {
    return (
      <div className="rounded-lg border bg-card p-6 text-sm text-destructive">
        Gagal memuat dashboard. Muat ulang untuk mencoba lagi.
      </div>
    )
  }

  const data = stats.data
  const isEmpty = data.assessments.total === 0

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Ringkasan</h2>
        <p className="text-sm text-muted-foreground">
          Cuplikan aktivitas pencocokan lokermu. Diperbarui tiap kunjungan.
        </p>
      </div>

      <PaymentGateBanner />
      {hasWaitingPayment && <WaitingPaymentBanner />}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Loker Tersedia"
          value={data.assessments.total}
          hint={
            data.assessments.today > 0
              ? `+${data.assessments.today} hari ini`
              : "Belum ada baru hari ini"
          }
        />
        <StatCard
          label="Skor rata-rata"
          value={data.assessments.avg_score || 0}
          suffix={data.assessments.total > 0 ? "/100" : ""}
        />
        <StatCard
          label="Pencarian Aktif"
          value={data.preferences.active_crawls}
          hint={`${data.preferences.total} total`}
        />
        <StatCard label="Loker dinilai" value={data.jobs_assessed} />
      </div>

      {isEmpty ? (
        <EmptyState />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Aktivitas</CardTitle>
                <CardDescription>30 hari terakhir</CardDescription>
              </CardHeader>
              <CardContent>
                <TrendChart data={data.trend_30d} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Per status</CardTitle>
                <CardDescription>
                  Distribusi di seluruh pipeline-mu
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
              <CardTitle>Distribusi skor</CardTitle>
              <CardDescription>
                Sebaran skor kecocokan kamu terhadap kebutuhan loker
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScoreDistribution buckets={data.score_buckets} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <div className="space-y-1">
                <CardTitle>Loker tersedia terbaru</CardTitle>
                <CardDescription>5 terakhir</CardDescription>
              </div>
              <Button asChild size="sm" variant="outline">
                <Link to="/assessments">Lihat semua</Link>
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
            tickFormatter={(d: string) =>
              new Date(d).toLocaleDateString("id-ID", {
                day: "2-digit",
                month: "short",
              })
            }
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
                ? new Date(d).toLocaleDateString("id-ID", {
                    day: "2-digit",
                    month: "short",
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
        Belum ada penilaian.
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

function WaitingPaymentBanner() {
  return (
    <Card className="border-primary/40 bg-primary/5">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <div className="space-y-1">
          <CardTitle className="text-base">Pencarian disetujui</CardTitle>
          <CardDescription>
            Pilih paket untuk mulai mencocokkan loker dengan profilmu.
          </CardDescription>
        </div>
        <Button asChild size="sm">
          <Link to="/plans">Pilih paket</Link>
        </Button>
      </CardHeader>
    </Card>
  )
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-start gap-3 py-10">
        <div>
          <h3 className="text-base font-semibold">Belum ada penilaian</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Tambah Pencarian untuk mulai mengambil loker dan menghasilkan
            kecocokan.
          </p>
        </div>
        <Button asChild size="sm">
          <Link to="/preferences">Kelola Pencarian</Link>
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
