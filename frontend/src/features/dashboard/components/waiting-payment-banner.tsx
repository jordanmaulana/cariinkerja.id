import { Link } from "@tanstack/react-router";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function WaitingPaymentBanner() {
  return (
    <Card className="border-primary/40 bg-primary/5">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <div className="space-y-1">
          <CardTitle className="text-base">Pencarian disetujui</CardTitle>
          <CardDescription>
            Pilih paket untuk mulai mencocokkan loker dengan profilmu.
          </CardDescription>
        </div>
        <Button asChild size="sm">
          <Link to="/plans">Pilih paket</Link>
        </Button>
      </CardHeader>
    </Card>
  );
}
