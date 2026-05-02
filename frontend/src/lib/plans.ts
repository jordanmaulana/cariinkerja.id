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
  | "CANCELLED";

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

export function formatRupiah(amount: number): string {
  return `Rp ${amount.toLocaleString("id-ID")}`;
}
