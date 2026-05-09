import { api, ApiError } from "@/lib/api";
import type {
  CheckoutResponse,
  PaymentGate,
  Plan,
  Subscription,
  UpgradeQuote,
} from "@/features/billing/types";

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

export async function getUpgradeQuote(planId: string): Promise<UpgradeQuote> {
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
