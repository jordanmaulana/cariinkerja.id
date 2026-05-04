import { api, ApiError } from "@/lib/api";

export type Plan = {
  id: string;
  name: string;
  price: number;
  effective_price: number;
  preference_limit: number;
};

export type SubscriptionStatus =
  | "PENDING"
  | "ACTIVE"
  | "EXPIRED"
  | "CANCELLED"
  | "REPLACED";

export type UpgradeQuote = {
  current_plan_id: string;
  new_plan_id: string;
  seconds_remaining: number;
  days_remaining: number;
  amount_paid_old: number;
  credit_value: number;
  bonus_seconds: number;
  bonus_days: number;
  charge: number;
  new_expires_at_estimate: string;
};

export type UpgradeQuoteError = {
  detail: string;
  code: "no_active_sub" | "downgrade" | "same_plan";
};

export type Subscription = {
  id: string;
  plan: Plan;
  status: SubscriptionStatus;
  started_at: string | null;
  expires_at: string | null;
  payment_link: string;
  created_on: string;
};

export type CheckoutResponse = {
  subscription_id: string;
  payment_link: string;
};

export type PaymentGateCode = "waiting_admin" | "linkedin_quality";

export type PaymentGate =
  | { locked: false }
  | { locked: true; code: PaymentGateCode; detail: string };

export async function getPaymentGate(): Promise<PaymentGate> {
  return api<PaymentGate>("/payment-gate/");
}

export async function listPlans(): Promise<Plan[]> {
  return api<Plan[]>("/plans/");
}

export async function getMySubscription(): Promise<Subscription | null> {
  try {
    return await api<Subscription>("/subscriptions/me/");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export async function checkout(planId: string): Promise<CheckoutResponse> {
  return api<CheckoutResponse>("/subscriptions/checkout/", {
    method: "POST",
    body: JSON.stringify({ plan_id: planId }),
  });
}

export async function getUpgradeQuote(
  planId: string,
): Promise<UpgradeQuote> {
  return api<UpgradeQuote>(
    `/subscriptions/upgrade-quote/?plan_id=${encodeURIComponent(planId)}`,
  );
}

export async function recheckSubscription(
  subscriptionId: string,
): Promise<Subscription> {
  return api<Subscription>(`/subscriptions/${subscriptionId}/recheck/`, {
    method: "POST",
  });
}

export async function cancelPendingSubscription(): Promise<{
  subscription_id: string;
}> {
  return api<{ subscription_id: string }>("/subscriptions/cancel-pending/", {
    method: "POST",
  });
}

export function formatRupiah(amount: number): string {
  return `Rp ${amount.toLocaleString("id-ID")}`;
}
