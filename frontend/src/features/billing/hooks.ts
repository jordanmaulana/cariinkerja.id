import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "react-toastify";

import {
  cancelPendingSubscription,
  checkout,
  getMySubscription,
  getPaymentGate,
  getUpgradeQuote,
  listPlans,
  recheckSubscription,
} from "@/features/billing/api";
import type { UpgradeQuote } from "@/features/billing/types";
import { listPreferences } from "@/features/preferences/api";

export function usePaymentGate() {
  return useQuery({
    queryKey: ["payment-gate"],
    queryFn: getPaymentGate,
    staleTime: 30_000,
  });
}

export function usePlans() {
  return useQuery({
    queryKey: ["plans"],
    queryFn: listPlans,
  });
}

export function useMySubscription() {
  return useQuery({
    queryKey: ["subscription", "me"],
    queryFn: getMySubscription,
    retry: false,
  });
}

export function useUpgradeQuotes(planIds: string[]) {
  const queries = useQueries({
    queries: planIds.map((planId) => ({
      queryKey: ["upgrade-quote", planId],
      queryFn: () => getUpgradeQuote(planId),
      retry: false,
      staleTime: 30_000,
    })),
  });
  const quoteByPlanId: Record<string, UpgradeQuote | undefined> = {};
  planIds.forEach((planId, i) => {
    quoteByPlanId[planId] = queries[i]?.data;
  });
  return { quoteByPlanId, queries };
}

export function useCheckoutMutation() {
  return useMutation({
    mutationFn: (planId: string) => checkout(planId),
    onSuccess: (data) => {
      window.location.href = data.payment_link;
    },
  });
}

export function useRecheckSubscriptionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subscriptionId: string) => recheckSubscription(subscriptionId),
    onSuccess: (data) => {
      queryClient.setQueryData(["subscription", "me"], data);
      if (data.status === "PENDING") {
        toast.warning(
          "Masih pending — pembayaranmu belum kami terima. Coba lagi sebentar.",
        );
      } else if (data.status === "ACTIVE") {
        toast.success("Langganan aktif.");
      }
    },
  });
}

export function useHasWaitingPayment() {
  const gate = usePaymentGate();
  const prefs = useQuery({
    queryKey: ["preferences"],
    queryFn: listPreferences,
  });
  return (
    !gate.data?.locked &&
    !!prefs.data?.some((p) => p.status === "waiting_payment")
  );
}

export function useCancelPendingMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => cancelPendingSubscription(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription", "me"] });
      toast.info("Langganan pending dibatalkan.");
    },
  });
}
