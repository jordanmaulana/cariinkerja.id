import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Clock } from "lucide-react"

import { getPaymentGate, type PaymentGate } from "@/lib/plans"

const TITLE: Record<
  Extract<PaymentGate, { locked: true }>["code"],
  string
> = {
  waiting_admin: "LinkedIn under admin review",
  linkedin_quality: "LinkedIn profile needs more detail",
}

export function usePaymentGate() {
  return useQuery({
    queryKey: ["payment-gate"],
    queryFn: getPaymentGate,
    staleTime: 30_000,
  })
}

export function PaymentGateBanner() {
  const { data } = usePaymentGate()
  if (!data || !data.locked) return null
  const Icon = data.code === "waiting_admin" ? Clock : AlertTriangle
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive-foreground"
    >
      <Icon className="mt-0.5 size-5 shrink-0 text-destructive" />
      <div className="space-y-1">
        <p className="font-semibold text-destructive">{TITLE[data.code]}</p>
        <p className="text-muted-foreground">
          {data.detail}
          {data.code === "waiting_admin" &&
            " You can pick a plan once your LinkedIn is approved."}
          {data.code === "linkedin_quality" &&
            " Update your LinkedIn profile and re-submit before paying."}
        </p>
      </div>
    </div>
  )
}
