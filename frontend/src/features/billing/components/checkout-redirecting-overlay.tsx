import { Loader2 } from "lucide-react";

export function CheckoutRedirectingOverlay() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 z-[90] flex flex-col items-center justify-center gap-3 bg-background/80 backdrop-blur-sm"
    >
      <Loader2 className="size-8 animate-spin text-primary" />
      <p className="text-sm font-medium">Mengarahkan ke pembayaran…</p>
      <p className="text-xs text-muted-foreground">
        Jangan tutup tab ini. Kami akan mengarahkanmu ke halaman checkout aman.
      </p>
    </div>
  );
}
