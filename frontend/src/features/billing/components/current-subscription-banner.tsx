import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { STATUS_LABEL, STATUS_VARIANT } from "@/features/billing/consts";
import type { Subscription } from "@/features/billing/types";

type Props = {
  sub: Subscription | null | undefined;
  loading: boolean;
  onRecheck: () => void;
  rechecking: boolean;
  recheckError: string | null;
  onCancel: () => void;
  cancelling: boolean;
  cancelError: string | null;
};

export function CurrentSubscriptionBanner({
  sub,
  loading,
  onRecheck,
  rechecking,
  recheckError,
  onCancel,
  cancelling,
  cancelError,
}: Props) {
  if (loading) return <Skeleton className="h-20 w-full" />;
  if (!sub) {
    return (
      <Card id="current-sub">
        <CardHeader>
          <CardTitle className="text-base">Belum ada langganan aktif</CardTitle>
          <CardDescription>
            Berlangganan di bawah untuk membuka pencocokan loker harian.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }
  const expires = sub.expires_at ? new Date(sub.expires_at) : null;
  return (
    <Card id="current-sub">
      <CardHeader className="flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-base">
            {sub.plan.name}{" "}
            <Badge variant={STATUS_VARIANT[sub.status]} className="ml-2">
              {STATUS_LABEL[sub.status]}
            </Badge>
          </CardTitle>
          <CardDescription>
            {sub.status === "ACTIVE" && expires && (
              <>Aktif sampai {expires.toLocaleDateString("id-ID")}</>
            )}
            {sub.status === "PENDING" && sub.payment_link && (
              <>
                Menunggu pembayaran.{" "}
                <a
                  href={sub.payment_link}
                  className="text-primary underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  Lanjutkan checkout
                </a>
              </>
            )}
            {sub.status === "EXPIRED" && (
              <>Langganan kedaluwarsa. Perpanjang di bawah.</>
            )}
            {sub.status === "CANCELLED" && <>Dibatalkan.</>}
            {sub.status === "REPLACED" && <>Diganti dengan paket lebih baru.</>}
          </CardDescription>
          {recheckError && (
            <p className="text-xs text-destructive">{recheckError}</p>
          )}
          {cancelError && (
            <p className="text-xs text-destructive">{cancelError}</p>
          )}
        </div>
        {sub.status === "PENDING" && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onRecheck}
              disabled={rechecking || cancelling}
            >
              {rechecking ? "Memeriksa…" : "Saya sudah bayar, refresh"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              disabled={rechecking || cancelling}
            >
              {cancelling ? "Membatalkan…" : "Batal"}
            </Button>
          </div>
        )}
      </CardHeader>
    </Card>
  );
}
