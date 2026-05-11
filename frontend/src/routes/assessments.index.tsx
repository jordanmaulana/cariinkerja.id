import { useMemo, useState } from "react"
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router"
import { Search } from "lucide-react"

import { useHasWaitingPayment } from "@/features/billing/hooks"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useAssessmentsList,
  useUpdateAssessmentStatusListMutation,
} from "@/features/assessments/hooks"
import {
  isAssessmentStatus,
  parseMinScoreInput,
  sortStatuses,
} from "@/features/assessments/utils"
import { AssessmentsTable } from "@/features/assessments/components/assessments-table"
import type { AssessmentStatus } from "@/features/assessments/types"
import {
  ASSESSMENT_STATUSES,
  STATUS_HINT,
  STATUS_LABEL,
} from "@/features/assessments/consts"

type AssessmentsSearch = {
  status?: AssessmentStatus[]
  status_all?: boolean
  min_score?: number
  page?: number
}

export const Route = createFileRoute("/assessments/")({
  validateSearch: (search: Record<string, unknown>): AssessmentsSearch => {
    const raw = search.status
    const arr = Array.isArray(raw) ? raw : raw == null ? [] : [raw]
    const status = arr.filter(isAssessmentStatus)

    const allCleared =
      search.status_all === "1" ||
      search.status_all === 1 ||
      search.status_all === true

    const ms = Number(search.min_score)
    const min_score =
      Number.isFinite(ms) && ms >= 0 && ms <= 100 ? Math.floor(ms) : undefined

    const p = Number(search.page)
    const page = Number.isFinite(p) && p >= 1 ? Math.floor(p) : undefined

    return {
      status: status.length ? status : undefined,
      status_all: allCleared || undefined,
      min_score,
      page,
    }
  },
  component: AssessmentsPage,
})

const PAGE_SIZE = 10

function AssessmentsPage() {
  const search = Route.useSearch()
  const navigate = useNavigate()

  const selectedStatuses = useMemo<Set<AssessmentStatus>>(() => {
    if (search.status_all) return new Set()
    if (search.status) return new Set(search.status)
    return new Set<AssessmentStatus>(["new"])
  }, [search.status, search.status_all])

  const [minScoreInput, setMinScoreInput] = useState(() =>
    search.min_score != null ? String(search.min_score) : "",
  )

  const page = search.page ?? 1
  const minScore = parseMinScoreInput(minScoreInput)
  const statuses = sortStatuses(selectedStatuses)

  const query = useAssessmentsList({
    statuses,
    minScore,
    page,
    pageSize: PAGE_SIZE,
  })

  const rows = query.data?.results
  const count = query.data?.count ?? 0
  const numPages = query.data?.num_pages ?? 1

  function toggleStatus(s: AssessmentStatus, checked: boolean) {
    const next = new Set(selectedStatuses)
    if (checked) next.add(s)
    else next.delete(s)
    const nextArr = sortStatuses(next)
    navigate({
      to: "/assessments",
      search: (prev) => ({
        ...prev,
        status: nextArr.length ? nextArr : undefined,
        status_all: nextArr.length === 0 ? true : undefined,
        page: undefined,
      }),
      replace: true,
    })
  }

  function handleMinScoreChange(value: string) {
    setMinScoreInput(value)
    const parsed = parseMinScoreInput(value)
    navigate({
      to: "/assessments",
      search: (prev) => ({
        ...prev,
        min_score: parsed,
        page: undefined,
      }),
      replace: true,
    })
  }

  function goToPage(p: number) {
    navigate({
      to: "/assessments",
      search: (prev) => ({ ...prev, page: p <= 1 ? undefined : p }),
    })
  }

  const mutation = useUpdateAssessmentStatusListMutation()
  const hasWaitingPayment = useHasWaitingPayment()

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Loker Tersedia</h2>
        <p className="text-sm text-muted-foreground">
          Loker yang cocok dengan Pencarianmu. Tandai satu per satu biar
          progresmu kelacak.
        </p>
      </div>

      {hasWaitingPayment && (
        <Card className="border-primary/40 bg-primary/5">
          <CardHeader className="flex-row items-center justify-between gap-3">
            <div className="space-y-1">
              <CardTitle className="text-base">
                Crawl gratis selesai
              </CardTitle>
              <CardDescription>
                Pilih paket untuk lanjut crawl loker selama 30 hari.
              </CardDescription>
            </div>
            <Button asChild size="sm">
              <Link to="/plans">Pilih paket</Link>
            </Button>
          </CardHeader>
        </Card>
      )}

      <Card>
        <CardHeader className="flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>
              {count} loker tersedia yang cocok
              {numPages > 1 && ` · Halaman ${page} dari ${numPages}`}
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
                placeholder="Skor min"
                title="Skor kecocokan dari LLM, 0–100"
                value={minScoreInput}
                onChange={(e) => handleMinScoreChange(e.target.value)}
                className="h-8 w-32 pl-7 text-xs"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-0">
          <p className="px-6 pb-3 text-xs text-muted-foreground">
            Status: {ASSESSMENT_STATUSES.map((s) => STATUS_LABEL[s]).join(" · ")}
          </p>
          {query.isLoading && (
            <div className="px-6 pb-6">
              <Skeleton className="h-32 w-full" />
            </div>
          )}
          {query.isError && (
            <p className="px-6 pb-6 text-sm text-destructive">
              Gagal memuat loker tersedia.
            </p>
          )}
          {rows && rows.length === 0 && !query.isLoading && (
            <p className="px-6 pb-6 text-sm text-muted-foreground">
              Tidak ada loker yang cocok dengan filter ini.
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
                Halaman {page} dari {numPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1 || query.isFetching}
                  onClick={() => goToPage(page - 1)}
                >
                  Sebelumnya
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= numPages || query.isFetching}
                  onClick={() => goToPage(page + 1)}
                >
                  Berikutnya
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
