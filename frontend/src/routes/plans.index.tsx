import { useCallback } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check } from "lucide-react"

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
  type Plan,
  type Subscription,
  checkout,
  formatRupiah,
  getMySubscription,
  listPlans,
  recheckSubscription,
} from "@/lib/plans"
import { useUserEvents, type UserEvent } from "@/lib/realtime"

export const Route = createFileRoute("/plans/")({
  component: PlansPage,
})

const STATUS_LABEL: Record<Subscription["status"], string> = {
  PENDING: "Pending payment",
  ACTIVE: "Active",
  EXPIRED: "Expired",
  CANCELLED: "Cancelled",
}

const STATUS_VARIANT: Record<
  Subscription["status"],
  "default" | "secondary" | "destructive" | "outline"
> = {
  PENDING: "secondary",
  ACTIVE: "default",
  EXPIRED: "outline",
  CANCELLED: "destructive",
}

function PlansPage() {
  const plansQuery = useQuery({
    queryKey: ["plans"],
    queryFn: listPlans,
  })
  const subQuery = useQuery({
    queryKey: ["subscription", "me"],
    queryFn: getMySubscription,
    retry: false,
  })

  const checkoutMutation = useMutation({
    mutationFn: (planId: string) => checkout(planId),
    onSuccess: (data) => {
      window.location.href = data.payment_link
    },
  })

  const queryClient = useQueryClient()
  const recheckMutation = useMutation({
    mutationFn: (subscriptionId: string) => recheckSubscription(subscriptionId),
    onSuccess: (data) => {
      queryClient.setQueryData(["subscription", "me"], data)
    },
  })

  useUserEvents(
    useCallback(
      (e: UserEvent) => {
        if (e.event === "subscription.activated") {
          queryClient.invalidateQueries({ queryKey: ["subscription", "me"] })
          queryClient.invalidateQueries({ queryKey: ["plans"] })
        }
      },
      [queryClient],
    ),
  )

  const sub = subQuery.data
  const activePlanId =
    sub && sub.status === "ACTIVE" ? sub.plan.id : null

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Plans</h2>
        <p className="text-sm text-muted-foreground">
          Pick a plan to start matching jobs to your profile.
        </p>
      </div>

      <CurrentSubscriptionBanner
        sub={sub}
        loading={subQuery.isLoading}
        onRecheck={() => sub && recheckMutation.mutate(sub.id)}
        rechecking={recheckMutation.isPending}
        recheckError={
          recheckMutation.isError && recheckMutation.error instanceof Error
            ? recheckMutation.error.message
            : null
        }
      />

      {plansQuery.isLoading && (
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-56 w-full" />
          ))}
        </div>
      )}
      {plansQuery.isError && (
        <p className="text-sm text-destructive">Failed to load plans.</p>
      )}
      {plansQuery.data && plansQuery.data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No plans available right now.
        </p>
      )}
      {plansQuery.data && plansQuery.data.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          {plansQuery.data.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isCurrent={plan.id === activePlanId}
              isPending={
                checkoutMutation.isPending &&
                checkoutMutation.variables === plan.id
              }
              onSubscribe={() => checkoutMutation.mutate(plan.id)}
            />
          ))}
        </div>
      )}
      {checkoutMutation.isError && (
        <p className="text-sm text-destructive">
          Could not start checkout.{" "}
          {checkoutMutation.error instanceof Error
            ? checkoutMutation.error.message
            : ""}
        </p>
      )}
    </div>
  )
}

function CurrentSubscriptionBanner({
  sub,
  loading,
  onRecheck,
  rechecking,
  recheckError,
}: {
  sub: Subscription | null | undefined
  loading: boolean
  onRecheck: () => void
  rechecking: boolean
  recheckError: string | null
}) {
  if (loading) return <Skeleton className="h-20 w-full" />
  if (!sub) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">No active subscription</CardTitle>
          <CardDescription>
            Subscribe below to unlock the daily job matcher.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }
  const expires = sub.expires_at ? new Date(sub.expires_at) : null
  return (
    <Card>
      <CardHeader className="flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-base">
            {sub.plan.name}{" "}
            <Badge variant={STATUS_VARIANT[sub.status]} className="ml-2">
              {STATUS_LABEL[sub.status]}
            </Badge>
          </CardTitle>
          <CardDescription>
            {sub.status === "ACTIVE" && expires && (
              <>Active until {expires.toLocaleDateString("id-ID")}</>
            )}
            {sub.status === "PENDING" && sub.payment_link && (
              <>
                Awaiting payment.{" "}
                <a
                  href={sub.payment_link}
                  className="text-primary underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  Resume checkout
                </a>
              </>
            )}
            {sub.status === "EXPIRED" && <>Subscription expired. Renew below.</>}
            {sub.status === "CANCELLED" && <>Cancelled.</>}
          </CardDescription>
          {recheckError && (
            <p className="text-xs text-destructive">{recheckError}</p>
          )}
        </div>
        {sub.status === "PENDING" && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRecheck}
            disabled={rechecking}
          >
            {rechecking ? "Checking…" : "I paid, refresh"}
          </Button>
        )}
      </CardHeader>
    </Card>
  )
}

function PlanCard({
  plan,
  isCurrent,
  isPending,
  onSubscribe,
}: {
  plan: Plan
  isCurrent: boolean
  isPending: boolean
  onSubscribe: () => void
}) {
  const discounted = plan.effective_price < plan.price
  return (
    <Card className={isCurrent ? "border-primary" : ""}>
      <CardHeader>
        <CardTitle>{plan.name}</CardTitle>
        <CardDescription>
          <span className="text-2xl font-semibold text-foreground">
            {formatRupiah(plan.effective_price)}
          </span>
          {discounted && (
            <span className="ml-2 text-sm text-muted-foreground line-through">
              {formatRupiah(plan.price)}
            </span>
          )}
          <span className="ml-1 text-sm text-muted-foreground">/ month</span>
          {discounted && (
            <Badge variant="secondary" className="ml-2">
              Open to Work
            </Badge>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-2 text-sm">
          <li className="flex items-center gap-2">
            <Check className="size-4 text-primary" />
            {plan.preference_limit}{" "}
            {plan.preference_limit === 1 ? "Finder" : "Finders"}
          </li>
          <li className="flex items-center gap-2">
            <Check className="size-4 text-primary" />
            Daily job matching + AI scoring
          </li>
          <li className="flex items-center gap-2">
            <Check className="size-4 text-primary" />
            30 days access
          </li>
        </ul>
        <Button
          className="w-full"
          disabled={isCurrent || isPending}
          onClick={onSubscribe}
        >
          {isCurrent
            ? "Current plan"
            : isPending
              ? "Redirecting…"
              : "Subscribe"}
        </Button>
      </CardContent>
    </Card>
  )
}
