import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { PaymentGateBanner } from "@/features/billing/components/payment-gate-banner"
import { NewPreferenceDialog } from "@/features/preferences/components/new-preference-dialog"
import { PreferencesTable } from "@/features/preferences/components/preferences-table"
import { listPreferences } from "@/features/preferences/api"

export const Route = createFileRoute("/preferences/")({
  component: PreferencesPage,
})

function PreferencesPage() {
  const navigate = useNavigate()
  const query = useQuery({
    queryKey: ["preferences"],
    queryFn: listPreferences,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">Pencarian</h2>
          <p className="text-sm text-muted-foreground">
            Tentukan apa yang kamu mau. Tiap Pencarian jadi feed crawl +
            kecocokan.
          </p>
        </div>
        <NewPreferenceDialog />
      </div>

      <PaymentGateBanner />

      <Card>
        <CardHeader>
          <CardTitle>Pencarianmu</CardTitle>
          <CardDescription>{query.data?.length ?? 0} total</CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          {query.isLoading && (
            <div className="px-6 pb-6">
              <Skeleton className="h-32 w-full" />
            </div>
          )}
          {query.isError && (
            <div className="px-6 pb-6 text-sm text-destructive">
              Gagal memuat Pencarian.
            </div>
          )}
          {query.data && query.data.length === 0 && (
            <div className="px-6 pb-6 text-sm text-muted-foreground">
              Belum ada Pencarian. Tambah satu untuk mulai crawling.
            </div>
          )}
          {query.data && query.data.length > 0 && (
            <PreferencesTable
              rows={query.data}
              onRowClick={(id) =>
                navigate({ to: "/preferences/$id", params: { id } })
              }
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
