import { createFileRoute, Link } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { PaymentGateBanner } from "@/features/billing/components/payment-gate-banner"
import { useHasWaitingPayment } from "@/features/billing/hooks"
import {
  useDashboardStats,
  useRecentAssessments,
} from "@/features/dashboard/hooks"
import { DashboardSkeleton } from "@/features/dashboard/components/dashboard-skeleton"
import { EmptyState } from "@/features/dashboard/components/empty-state"
import { RecentList } from "@/features/dashboard/components/recent-list"
import { ScoreDistribution } from "@/features/dashboard/components/score-distribution"
import { StatCard } from "@/features/dashboard/components/stat-card"
import { StatusBreakdown } from "@/features/dashboard/components/status-breakdown"
import { TrendChart } from "@/features/dashboard/components/trend-chart"
import { WaitingPaymentBanner } from "@/features/dashboard/components/waiting-payment-banner"

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
})

function DashboardPage() {
  const stats = useDashboardStats()
  const recent = useRecentAssessments()
  const hasWaitingPayment = useHasWaitingPayment()

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
