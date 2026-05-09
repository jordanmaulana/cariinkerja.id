import { Link, createFileRoute } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { PaymentGateBanner } from "@/features/billing/components/payment-gate-banner"
import { PreferenceEditor } from "@/features/preferences/components/preference-editor"
import { StateNotice } from "@/features/preferences/components/state-notice"
import { getPreference } from "@/features/preferences/api"
import { STATUS_LABEL, STATUS_VARIANT } from "@/features/preferences/consts"

export const Route = createFileRoute("/preferences/$id")({
  component: PreferenceDetailPage,
})

function PreferenceDetailPage() {
  const { id } = Route.useParams()

  const query = useQuery({
    queryKey: ["preference", id],
    queryFn: () => getPreference(id),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/preferences">
            <ArrowLeft className="size-4" />
            Kembali ke Pencarian
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
            Gagal memuat Pencarian. Mungkin tidak ada.
          </CardContent>
        </Card>
      )}

      {query.data && <StateNotice preference={query.data} />}
      <PaymentGateBanner />

      {query.data && <PreferenceEditor key={query.data.id} preference={query.data} />}
    </div>
  )
}
