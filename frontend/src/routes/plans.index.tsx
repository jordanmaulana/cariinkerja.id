import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query"
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import {
  type Plan,
  type PaymentGate,
  type Subscription,
  type UpgradeQuote,
  cancelPendingSubscription,
  checkout,
  formatRupiah,
  getMySubscription,
  getUpgradeQuote,
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
  REPLACED: "Replaced",
}

const STATUS_VARIANT: Record<
  Subscription["status"],
  "default" | "secondary" | "destructive" | "outline"
> = {
  PENDING: "secondary",
  ACTIVE: "default",
  EXPIRED: "outline",
  CANCELLED: "destructive",
  REPLACED: "outline",
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

type PlanMode =
  | "buy"
  | "current"
  | "upgrade"
  | "downgrade-blocked"
  | "pending-other"
  | "locked"

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

  const sub = subQuery.data
  const activePlan =
    sub && sub.status === "ACTIVE" ? sub.plan : null
  const pendingPlanId =
    sub && sub.status === "PENDING" ? sub.plan.id : null
  const hasPendingSub = pendingPlanId !== null

  const upgradeablePlanIds =
    activePlan && plansQuery.data
      ? plansQuery.data
          .filter((p) => p.price > activePlan.price && p.id !== activePlan.id)
          .map((p) => p.id)
      : []

  const quoteQueries = useQueries({
    queries: upgradeablePlanIds.map((planId) => ({
      queryKey: ["upgrade-quote", planId],
      queryFn: () => getUpgradeQuote(planId),
      retry: false,
      staleTime: 30_000,
    })),
  })
  const quoteByPlanId: Record<string, UpgradeQuote | undefined> = {}
  upgradeablePlanIds.forEach((planId, i) => {
    quoteByPlanId[planId] = quoteQueries[i]?.data
  })

  const [confirmingPlanId, setConfirmingPlanId] = useState<string | null>(null)

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

  function modeFor(plan: Plan): PlanMode {
    if (locked) return "locked"
    if (activePlan && plan.id === activePlan.id) return "current"
    if (hasPendingSub && plan.id !== pendingPlanId) return "pending-other"
    if (activePlan) {
      if (plan.price > activePlan.price) return "upgrade"
      if (plan.price < activePlan.price) return "downgrade-blocked"
    }
    return "buy"
  }

  const confirmingPlan =
    confirmingPlanId && plansQuery.data
      ? plansQuery.data.find((p) => p.id === confirmingPlanId) ?? null
      : null
  const confirmingQuote = confirmingPlanId
    ? quoteByPlanId[confirmingPlanId]
    : undefined

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
          {plansQuery.data.map((plan) => {
            const mode = modeFor(plan)
            const quote = quoteByPlanId[plan.id]
            return (
              <PlanCard
                key={plan.id}
                plan={plan}
                mode={mode}
                upgradeQuote={mode === "upgrade" ? quote : undefined}
                isCheckoutPending={
                  checkoutMutation.isPending &&
                  checkoutMutation.variables === plan.id
                }
                lockedReason={lockedReason}
                onSubscribe={() => checkoutMutation.mutate(plan.id)}
                onUpgradeClick={() => setConfirmingPlanId(plan.id)}
              />
            )
          })}
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

      <UpgradeConfirmDialog
        plan={confirmingPlan}
        quote={confirmingQuote}
        currentPlanName={activePlan?.name ?? null}
        open={confirmingPlanId !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmingPlanId(null)
        }}
        onConfirm={() => {
          if (confirmingPlanId) checkoutMutation.mutate(confirmingPlanId)
          setConfirmingPlanId(null)
        }}
      />
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
            {sub.status === "REPLACED" && <>Replaced by a newer plan.</>}
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

function buttonLabelFor(
  mode: PlanMode,
  isCheckoutPending: boolean,
  charge: number | null,
): string {
  if (isCheckoutPending) return "Redirecting…"
  switch (mode) {
    case "current":
      return "Current plan"
    case "pending-other":
      return "Resume or cancel pending ↑"
    case "locked":
      return "Locked"
    case "upgrade":
      return charge != null ? `Upgrade — ${formatRupiah(charge)}` : "Upgrade"
    case "downgrade-blocked":
      return "Downgrade not available"
    case "buy":
    default:
      return "Buy plan"
  }
}

function PlanCard({
  plan,
  mode,
  upgradeQuote,
  isCheckoutPending,
  lockedReason,
  onSubscribe,
  onUpgradeClick,
}: {
  plan: Plan
  mode: PlanMode
  upgradeQuote: UpgradeQuote | undefined
  isCheckoutPending: boolean
  lockedReason: string | null
  onSubscribe: () => void
  onUpgradeClick: () => void
}) {
  const discounted = plan.effective_price < plan.price
  const showUpgradeBreakdown = mode === "upgrade" && upgradeQuote
  const charge = showUpgradeBreakdown ? upgradeQuote.charge : null
  const label = buttonLabelFor(mode, isCheckoutPending, charge)
  const buttonTitle =
    mode === "locked"
      ? lockedReason ?? undefined
      : mode === "pending-other"
        ? "You have a pending subscription. Scroll up to resume or cancel it first."
        : mode === "downgrade-blocked"
          ? "Downgrades are not supported. Wait for the current plan to expire."
          : undefined
  const disabled =
    mode === "current" ||
    mode === "downgrade-blocked" ||
    mode === "locked" ||
    isCheckoutPending
  return (
    <Card className={mode === "current" ? "border-primary" : ""}>
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
        {discounted && mode !== "upgrade" && (
          <p className="mt-1 text-xs text-muted-foreground">
            Open-to-Work pricing — auto-applied while you have no active subscription.
          </p>
        )}
        {showUpgradeBreakdown && (
          <div className="mt-3 rounded-md border border-dashed p-3 text-xs space-y-1">
            <div className="flex justify-between">
              <span>List price</span>
              <span>{formatRupiah(plan.price)}</span>
            </div>
            <div className="flex justify-between text-emerald-600">
              <span>+ Bonus from current plan</span>
              <span>
                ~{upgradeQuote.bonus_days.toFixed(1)}d
                {" "}
                <span className="text-muted-foreground">
                  ({formatRupiah(upgradeQuote.credit_value)} credit)
                </span>
              </span>
            </div>
            <div className="flex justify-between font-medium pt-1 border-t">
              <span>Pay now</span>
              <span>{formatRupiah(upgradeQuote.charge)}</span>
            </div>
          </div>
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
            {showUpgradeBreakdown &&
              ` + ~${upgradeQuote.bonus_days.toFixed(1)} bonus days`}
          </li>
        </ul>
        {mode === "pending-other" ? (
          <Button asChild className="w-full" variant="secondary">
            <a href="#current-sub" title={buttonTitle}>
              {label}
            </a>
          </Button>
        ) : (
          <Button
            className="w-full"
            disabled={disabled}
            onClick={mode === "upgrade" ? onUpgradeClick : onSubscribe}
            title={buttonTitle}
            variant={mode === "downgrade-blocked" ? "outline" : "default"}
          >
            {label}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

function UpgradeConfirmDialog({
  plan,
  quote,
  currentPlanName,
  open,
  onOpenChange,
  onConfirm,
}: {
  plan: Plan | null
  quote: UpgradeQuote | undefined
  currentPlanName: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}) {
  if (!plan) return null
  const eta = quote
    ? new Date(quote.new_expires_at_estimate).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upgrade to {plan.name}</DialogTitle>
          <DialogDescription>
            {currentPlanName
              ? `Your ${currentPlanName} ends now. ${plan.name} starts immediately with bonus days from unused credit.`
              : `Confirm your upgrade to ${plan.name}.`}
          </DialogDescription>
        </DialogHeader>
        {quote ? (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>{plan.name} list price</span>
              <span>{formatRupiah(plan.price)}</span>
            </div>
            <div className="flex justify-between text-emerald-600">
              <span>
                Credit from {currentPlanName ?? "current plan"} ({quote.days_remaining.toFixed(1)}d
                left)
              </span>
              <span>{formatRupiah(quote.credit_value)}</span>
            </div>
            <div className="flex justify-between text-emerald-600">
              <span>Bonus days on {plan.name}</span>
              <span>~{quote.bonus_days.toFixed(1)}d</span>
            </div>
            <div className="flex justify-between border-t pt-2 font-medium">
              <span>Pay now</span>
              <span>{formatRupiah(quote.charge)}</span>
            </div>
            {eta && (
              <p className="pt-1 text-xs text-muted-foreground">
                {plan.name} runs until ~{eta}.
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Final bonus is calculated when payment confirms — paying later means slightly fewer bonus days.
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Loading quote…</p>
        )}
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={!quote}>
            Continue to payment
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
