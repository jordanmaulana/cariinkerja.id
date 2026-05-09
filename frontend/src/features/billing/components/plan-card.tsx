import { Check } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { OPEN_TO_WORK_HINT } from "@/features/billing/consts";
import type { Plan, UpgradeQuote } from "@/features/billing/types";
import { formatRupiah } from "@/features/billing/utils";
import type { PlanMode } from "@/features/billing/types";

export type { PlanMode };

function buttonLabelFor(
  mode: PlanMode,
  isCheckoutPending: boolean,
  charge: number | null,
): string {
  if (isCheckoutPending) return "Mengarahkan…";
  switch (mode) {
    case "current":
      return "Paket saat ini";
    case "pending-other":
      return "Lanjutkan atau batalkan pending ↑";
    case "locked":
      return "Terkunci";
    case "upgrade":
      return charge != null ? `Upgrade — ${formatRupiah(charge)}` : "Upgrade";
    case "downgrade-blocked":
      return "Downgrade tidak tersedia";
    case "buy":
    default:
      return "Beli paket";
  }
}

type Props = {
  plan: Plan;
  mode: PlanMode;
  upgradeQuote: UpgradeQuote | undefined;
  isCheckoutPending: boolean;
  lockedReason: string | null;
  onSubscribe: () => void;
  onUpgradeClick: () => void;
};

export function PlanCard({
  plan,
  mode,
  upgradeQuote,
  isCheckoutPending,
  lockedReason,
  onSubscribe,
  onUpgradeClick,
}: Props) {
  const discounted = plan.effective_price < plan.price;
  const showUpgradeBreakdown = mode === "upgrade" && upgradeQuote;
  const charge = showUpgradeBreakdown ? upgradeQuote.charge : null;
  const label = buttonLabelFor(mode, isCheckoutPending, charge);
  const buttonTitle =
    mode === "locked"
      ? lockedReason ?? undefined
      : mode === "pending-other"
        ? "Kamu punya langganan pending. Scroll ke atas untuk melanjutkan atau membatalkannya dulu."
        : mode === "downgrade-blocked"
          ? "Downgrade tidak didukung. Tunggu paket saat ini kedaluwarsa."
          : undefined;
  const disabled =
    mode === "current" ||
    mode === "downgrade-blocked" ||
    mode === "locked" ||
    isCheckoutPending;
  return (
    <Card className={mode === "current" ? "border-primary" : ""}>
      <CardHeader>
        <CardTitle>{plan.name}</CardTitle>
        <CardDescription>
          <span className="text-2xl font-semibold text-foreground">
            {formatRupiah(plan.effective_price)}
          </span>
          {discounted && (
            <span className="ml-2 text-sm text-muted-foreground line-through">
              {formatRupiah(plan.price)}
            </span>
          )}
          <span className="ml-1 text-sm text-muted-foreground">/ bulan</span>
          {discounted && (
            <Badge
              variant="secondary"
              className="ml-2 cursor-help"
              title={OPEN_TO_WORK_HINT}
            >
              Open to Work
            </Badge>
          )}
        </CardDescription>
        {discounted && mode !== "upgrade" && (
          <p className="mt-1 text-xs text-muted-foreground">
            Harga Open-to-Work — otomatis berlaku selama belum ada langganan aktif.
          </p>
        )}
        {showUpgradeBreakdown && (
          <div className="mt-3 rounded-md border border-dashed p-3 text-xs space-y-1">
            <div className="flex justify-between">
              <span>Harga normal</span>
              <span>{formatRupiah(plan.price)}</span>
            </div>
            <div className="flex justify-between text-emerald-600">
              <span>+ Bonus dari paket saat ini</span>
              <span>
                ~{upgradeQuote.bonus_days.toFixed(1)} hari{" "}
                <span className="text-muted-foreground">
                  ({formatRupiah(upgradeQuote.credit_value)} kredit)
                </span>
              </span>
            </div>
            <div className="flex justify-between font-medium pt-1 border-t">
              <span>Bayar sekarang</span>
              <span>{formatRupiah(upgradeQuote.charge)}</span>
            </div>
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-2 text-sm">
          <li className="flex items-center gap-2">
            <Check className="size-4 text-primary" />
            {plan.preference_limit} Pencarian
          </li>
          <li className="flex items-center gap-2">
            <Check className="size-4 text-primary" />
            Pencocokan loker harian + skor AI
          </li>
          <li className="flex items-center gap-2">
            <Check className="size-4 text-primary" />
            Akses 30 hari
            {showUpgradeBreakdown &&
              ` + ~${upgradeQuote.bonus_days.toFixed(1)} hari bonus`}
          </li>
        </ul>
        {mode === "pending-other" ? (
          <Button asChild className="w-full" variant="secondary">
            <a href="#current-sub" title={buttonTitle}>
              {label}
            </a>
          </Button>
        ) : (
          <Button
            className="w-full"
            disabled={disabled}
            onClick={mode === "upgrade" ? onUpgradeClick : onSubscribe}
            title={buttonTitle}
            variant={mode === "downgrade-blocked" ? "outline" : "default"}
          >
            {label}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
