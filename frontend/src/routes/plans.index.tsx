import { createFileRoute } from "@tanstack/react-router"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Loader2 } from "lucide-react"

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
import {
  type Plan,
  type PaymentGate,
  type Subscription,
  cancelPendingSubscription,
  checkout,
  formatRupiah,
  getMySubscription,
  listPlans,
  recheckSubscription,
} from "@/lib/plans"
import { toast } from "react-toastify"

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

const GATE_REASON: Record<
  Extract<PaymentGate, { locked: true }>["code"],
  string
> = {
  waiting_admin: "LinkedIn under admin review — wait for approval before subscribing.",
  linkedin_quality: "LinkedIn profile needs more detail before you can subscribe.",
}

const OPEN_TO_WORK_HINT =
  "Open-to-Work discount is applied automatically while you don't have an active subscription. Renewals at full price."

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
  const gateQuery = usePaymentGate()
  const locked = gateQuery.data?.locked === true
  const lockedReason =
    gateQuery.data?.locked === true ? GATE_REASON[gateQuery.data.code] : null

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
      if (data.status === "PENDING") {
        toast.warning(
          "Still pending — we haven't received your payment yet. Try again in a moment.",
        )
      } else if (data.status === "ACTIVE") {
        toast.success("Subscription activated.")
      }
    },
  })
  const cancelMutation = useMutation({
    mutationFn: () => cancelPendingSubscription(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription", "me"] })
      toast.info("Pending subscription cancelled.")
    },
  })

  const sub = subQuery.data
  const activePlanId =
    sub && sub.status === "ACTIVE" ? sub.plan.id : null
  const pendingPlanId =
    sub && sub.status === "PENDING" ? sub.plan.id : null
  const hasPendingSub = pendingPlanId !== null

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Plans</h2>
        <p className="text-sm text-muted-foreground">
          Pick a plan to start matching jobs to your profile.
        </p>
      </div>

      <PaymentGateBanner />

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
        onCancel={() => cancelMutation.mutate()}
        cancelling={cancelMutation.isPending}
        cancelError={
          cancelMutation.isError && cancelMutation.error instanceof Error
            ? cancelMutation.error.message
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
              isPendingOther={hasPendingSub && plan.id !== pendingPlanId}
              locked={locked}
              lockedReason={lockedReason}
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

      {checkoutMutation.isPending && <CheckoutRedirectingOverlay />}
    </div>
  )
}

function CheckoutRedirectingOverlay() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 z-[90] flex flex-col items-center justify-center gap-3 bg-background/80 backdrop-blur-sm"
    >
      <Loader2 className="size-8 animate-spin text-primary" />
      <p className="text-sm font-medium">Redirecting to payment…</p>
      <p className="text-xs text-muted-foreground">
        Don't close this tab. We'll send you to the secure checkout page.
      </p>
    </div>
  )
}

function CurrentSubscriptionBanner({
  sub,
  loading,
  onRecheck,
  rechecking,
  recheckError,
  onCancel,
  cancelling,
  cancelError,
}: {
  sub: Subscription | null | undefined
  loading: boolean
  onRecheck: () => void
  rechecking: boolean
  recheckError: string | null
  onCancel: () => void
  cancelling: boolean
  cancelError: string | null
}) {
  if (loading) return <Skeleton className="h-20 w-full" />
  if (!sub) {
    return (
      <Card id="current-sub">
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
    <Card id="current-sub">
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
          {cancelError && (
            <p className="text-xs text-destructive">{cancelError}</p>
          )}
        </div>
        {sub.status === "PENDING" && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onRecheck}
              disabled={rechecking || cancelling}
            >
              {rechecking ? "Checking…" : "I paid, refresh"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              disabled={rechecking || cancelling}
            >
              {cancelling ? "Cancelling…" : "Cancel"}
            </Button>
          </div>
        )}
      </CardHeader>
    </Card>
  )
}

function PlanCard({
  plan,
  isCurrent,
  isPending,
  isPendingOther,
  locked,
  lockedReason,
  onSubscribe,
}: {
  plan: Plan
  isCurrent: boolean
  isPending: boolean
  isPendingOther: boolean
  locked: boolean
  lockedReason: string | null
  onSubscribe: () => void
}) {
  const discounted = plan.effective_price < plan.price
  const buttonLabel = isCurrent
    ? "Current plan"
    : isPending
      ? "Redirecting…"
      : isPendingOther
        ? "Resume or cancel pending ↑"
        : locked
          ? "Locked"
          : "Buy plan"
  const buttonTitle = locked && !isCurrent && !isPending && !isPendingOther
    ? lockedReason ?? undefined
    : isPendingOther
      ? "You have a pending subscription. Scroll up to resume or cancel it first."
      : undefined
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
            <Badge
              variant="secondary"
              className="ml-2 cursor-help"
              title={OPEN_TO_WORK_HINT}
            >
              Open to Work
            </Badge>
          )}
        </CardDescription>
        {discounted && (
          <p className="mt-1 text-xs text-muted-foreground">
            Open-to-Work pricing — auto-applied while you have no active subscription.
          </p>
        )}
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
        {isPendingOther ? (
          <Button asChild className="w-full" variant="secondary">
            <a href="#current-sub" title={buttonTitle}>
              {buttonLabel}
            </a>
          </Button>
        ) : (
          <Button
            className="w-full"
            disabled={isCurrent || isPending || locked}
            onClick={onSubscribe}
            title={buttonTitle}
          >
            {buttonLabel}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
