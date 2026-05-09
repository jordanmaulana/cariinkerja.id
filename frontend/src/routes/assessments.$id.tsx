import { Link, createFileRoute } from "@tanstack/react-router"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  getAssessment,
  updateAssessmentStatus,
} from "@/features/assessments/api"
import { AssessmentDetail } from "@/features/assessments/components/assessment-detail"
import type { AssessmentStatus } from "@/features/assessments/types"
import { STATUS_LABEL, STATUS_VARIANT } from "@/features/assessments/consts"

export const Route = createFileRoute("/assessments/$id")({
  component: AssessmentDetailPage,
})

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
