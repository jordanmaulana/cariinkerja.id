import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Plan, UpgradeQuote } from "@/features/billing/types";
import { formatRupiah } from "@/features/billing/utils";

type Props = {
  plan: Plan | null;
  quote: UpgradeQuote | undefined;
  currentPlanName: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
};

export function UpgradeConfirmDialog({
  plan,
  quote,
  currentPlanName,
  open,
  onOpenChange,
  onConfirm,
}: Props) {
  if (!plan) return null;
  const eta = quote
    ? new Date(quote.new_expires_at_estimate).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upgrade ke {plan.name}</DialogTitle>
          <DialogDescription>
            {currentPlanName
              ? `${currentPlanName} milikmu berakhir sekarang. ${plan.name} langsung jalan dengan hari bonus dari kredit yang belum terpakai.`
              : `Konfirmasi upgrade ke ${plan.name}.`}
          </DialogDescription>
        </DialogHeader>
        {quote ? (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Harga normal {plan.name}</span>
              <span>{formatRupiah(plan.price)}</span>
            </div>
            <div className="flex justify-between text-emerald-600">
              <span>
                Kredit dari {currentPlanName ?? "paket saat ini"} (
                {quote.days_remaining.toFixed(1)} hari tersisa)
              </span>
              <span>{formatRupiah(quote.credit_value)}</span>
            </div>
            <div className="flex justify-between text-emerald-600">
              <span>Hari bonus di {plan.name}</span>
              <span>~{quote.bonus_days.toFixed(1)} hari</span>
            </div>
            <div className="flex justify-between border-t pt-2 font-medium">
              <span>Bayar sekarang</span>
              <span>{formatRupiah(quote.charge)}</span>
            </div>
            {eta && (
              <p className="pt-1 text-xs text-muted-foreground">
                {plan.name} berjalan sampai ~{eta}.
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Bonus final dihitung saat pembayaran terkonfirmasi — semakin lama bayar, hari bonusnya sedikit lebih sedikit.
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Memuat penawaran…</p>
        )}
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Batal
          </Button>
          <Button onClick={onConfirm} disabled={!quote}>
            Lanjut ke pembayaran
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
