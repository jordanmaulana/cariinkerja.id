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

export type PlanMode =
  | "buy"
  | "current"
  | "upgrade"
  | "downgrade-blocked"
  | "pending-other"
  | "locked";

export type PaymentGateCode = "waiting_admin" | "linkedin_quality";

export type PaymentGate =
  | { locked: false }
  | { locked: true; code: PaymentGateCode; detail: string };
