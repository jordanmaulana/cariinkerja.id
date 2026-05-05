import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Clock } from "lucide-react"

import { getPaymentGate, type PaymentGate } from "@/lib/plans"
import { cn } from "@/lib/utils"

type GateCode = Extract<PaymentGate, { locked: true }>["code"]

const TITLE: Record<GateCode, string> = {
  waiting_admin: "LinkedIn sedang ditinjau admin",
  linkedin_quality: "Profil LinkedIn perlu lebih lengkap",
}

const VARIANT_CLS: Record<GateCode, { wrap: string; title: string; icon: string; body: string }> = {
  waiting_admin: {
    wrap: "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950",
    title: "text-amber-900 dark:text-amber-100",
    icon: "text-amber-600 dark:text-amber-300",
    body: "text-amber-900/80 dark:text-amber-100/80",
  },
  linkedin_quality: {
    wrap: "border-destructive/40 bg-destructive/5",
    title: "text-destructive",
    icon: "text-destructive",
    body: "text-muted-foreground",
  },
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
  const cls = VARIANT_CLS[data.code]
  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded-lg border p-4 text-sm",
        cls.wrap,
      )}
    >
      <Icon className={cn("mt-0.5 size-5 shrink-0", cls.icon)} />
      <div className="space-y-1">
        <p className={cn("font-semibold", cls.title)}>{TITLE[data.code]}</p>
        <p className={cls.body}>
          {data.detail}
          {data.code === "waiting_admin" &&
            " Kamu bisa pilih paket setelah LinkedIn-mu disetujui."}
          {data.code === "linkedin_quality" &&
            " Lengkapi profil LinkedIn-mu dan kirim ulang sebelum bayar."}
        </p>
      </div>
    </div>
  )
}

export function paymentGateMessage(data: PaymentGate | undefined): string | null {
  if (!data || !data.locked) return null
  return TITLE[data.code]
}
