import type {
  Plan,
  PlanMode,
  Subscription,
} from "@/features/billing/types";

export function formatRupiah(amount: number): string {
  return `Rp ${amount.toLocaleString("id-ID")}`;
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
    .filter((p) => p.price > activePlan.price && p.id !== activePlan.id)
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
    if (plan.price > activePlan.price) return "upgrade";
    if (plan.price < activePlan.price) return "downgrade-blocked";
  }
  return "buy";
}
