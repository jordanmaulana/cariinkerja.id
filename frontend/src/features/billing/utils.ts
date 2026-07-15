import type {
  Plan,
  PlanMode,
  Subscription,
} from "@/features/billing/types";

export function formatRupiah(amount: number): string {
  return `Rp ${amount.toLocaleString("id-ID")}`;
}

export function durationLabel(days: number): string {
  return days === 30 ? "bulan" : `${days} hari`;
}

export function getActivePlan(
  sub: Subscription | null | undefined,
): Plan | null {
  return sub && sub.status === "ACTIVE" ? sub.plan : null;
}

export function getPendingPlanId(
  sub: Subscription | null | undefined,
): string | null {
  return sub && sub.status === "PENDING" ? sub.plan.id : null;
}

export function getUpgradeablePlanIds(
  activePlan: Plan | null,
  plans: Plan[] | undefined,
): string[] {
  if (!activePlan || !plans) return [];
  return plans
    .filter(
      (p) =>
        p.preference_limit > activePlan.preference_limit &&
        p.id !== activePlan.id,
    )
    .map((p) => p.id);
}

export function getPlanMode(args: {
  plan: Plan;
  locked: boolean;
  activePlan: Plan | null;
  hasPendingSub: boolean;
  pendingPlanId: string | null;
}): PlanMode {
  const { plan, locked, activePlan, hasPendingSub, pendingPlanId } = args;
  if (locked) return "locked";
  if (activePlan && plan.id === activePlan.id) return "current";
  if (hasPendingSub && plan.id !== pendingPlanId) return "pending-other";
  if (activePlan) {
    // Mirrors the backend guard in billing/upgrades.py: more preference slots
    // is the only upgrade. Same-slot moves across durations are not offered.
    if (plan.preference_limit > activePlan.preference_limit) return "upgrade";
    return "downgrade-blocked";
  }
  return "buy";
}
