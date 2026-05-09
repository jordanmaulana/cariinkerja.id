import { useQuery } from "@tanstack/react-query";

import { getPaymentGate } from "@/features/billing/api";

export function usePaymentGate() {
  return useQuery({
    queryKey: ["payment-gate"],
    queryFn: getPaymentGate,
    staleTime: 30_000,
  });
}
