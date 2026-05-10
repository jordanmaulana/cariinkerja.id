import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"

import { Skeleton } from "@/components/ui/skeleton"
import { CheckoutRedirectingOverlay } from "@/features/billing/components/checkout-redirecting-overlay"
import { CurrentSubscriptionBanner } from "@/features/billing/components/current-subscription-banner"
import { PaymentGateBanner } from "@/features/billing/components/payment-gate-banner"
import { PlanCard } from "@/features/billing/components/plan-card"
import { UpgradeConfirmDialog } from "@/features/billing/components/upgrade-confirm-dialog"
import {
  useCancelPendingMutation,
  useCheckoutMutation,
  useMySubscription,
  usePaymentGate,
  usePlans,
  useRecheckSubscriptionMutation,
  useUpgradeQuotes,
} from "@/features/billing/hooks"
import {
  getActivePlan,
  getPendingPlanId,
  getPlanMode,
  getUpgradeablePlanIds,
} from "@/features/billing/utils"
import { GATE_REASON } from "@/features/billing/consts"

export const Route = createFileRoute("/plans/")({
  component: PlansPage,
})

function PlansPage() {
  const plansQuery = usePlans()
  const subQuery = useMySubscription()
  const gateQuery = usePaymentGate()

  const locked = gateQuery.data?.locked === true
  const lockedReason =
    gateQuery.data?.locked === true ? GATE_REASON[gateQuery.data.code] : null

  const sub = subQuery.data
  const activePlan = getActivePlan(sub)
  const pendingPlanId = getPendingPlanId(sub)
  const hasPendingSub = pendingPlanId !== null

  const upgradeablePlanIds = getUpgradeablePlanIds(activePlan, plansQuery.data)
  const { quoteByPlanId } = useUpgradeQuotes(upgradeablePlanIds)

  const [confirmingPlanId, setConfirmingPlanId] = useState<string | null>(null)

  const checkoutMutation = useCheckoutMutation()
  const recheckMutation = useRecheckSubscriptionMutation()
  const cancelMutation = useCancelPendingMutation()

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
        <h2 className="text-2xl font-semibold tracking-tight">Paket</h2>
        <p className="text-sm text-muted-foreground">
          Pilih paket untuk mulai mencocokkan loker dengan profilmu.
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
        <p className="text-sm text-destructive">Gagal memuat paket.</p>
      )}
      {plansQuery.data && plansQuery.data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Belum ada paket tersedia saat ini.
        </p>
      )}
      {plansQuery.data && plansQuery.data.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          {plansQuery.data.map((plan) => {
            const mode = getPlanMode({
              plan,
              locked,
              activePlan,
              hasPendingSub,
              pendingPlanId,
            })
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
          Gagal memulai checkout.{" "}
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
