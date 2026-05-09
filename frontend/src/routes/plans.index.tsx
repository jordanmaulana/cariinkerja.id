import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "react-toastify"

import { Skeleton } from "@/components/ui/skeleton"
import { CheckoutRedirectingOverlay } from "@/features/billing/components/checkout-redirecting-overlay"
import { CurrentSubscriptionBanner } from "@/features/billing/components/current-subscription-banner"
import { PaymentGateBanner } from "@/features/billing/components/payment-gate-banner"
import { PlanCard, type PlanMode } from "@/features/billing/components/plan-card"
import { UpgradeConfirmDialog } from "@/features/billing/components/upgrade-confirm-dialog"
import { usePaymentGate } from "@/features/billing/hooks"
import {
  cancelPendingSubscription,
  checkout,
  getMySubscription,
  getUpgradeQuote,
  listPlans,
  recheckSubscription,
} from "@/features/billing/api"
import type { Plan, UpgradeQuote } from "@/features/billing/types"
import { GATE_REASON } from "@/features/billing/consts"

export const Route = createFileRoute("/plans/")({
  component: PlansPage,
})

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
  const activePlan = sub && sub.status === "ACTIVE" ? sub.plan : null
  const pendingPlanId = sub && sub.status === "PENDING" ? sub.plan.id : null
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
          "Masih pending — pembayaranmu belum kami terima. Coba lagi sebentar.",
        )
      } else if (data.status === "ACTIVE") {
        toast.success("Langganan aktif.")
      }
    },
  })
  const cancelMutation = useMutation({
    mutationFn: () => cancelPendingSubscription(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription", "me"] })
      toast.info("Langganan pending dibatalkan.")
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
