import { Link } from "@tanstack/react-router";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Preference } from "@/features/preferences/types";

export function StateNotice({ preference }: { preference: Preference }) {
  if (preference.status === "waiting_admin") {
    return (
      <Card className="border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950">
        <CardHeader>
          <CardTitle className="text-base text-amber-900 dark:text-amber-100">
            Lagi ngumpulin loker yang kamu cari
          </CardTitle>
          <CardDescription className="text-amber-900/80 dark:text-amber-100/80">
            Coba liat paketnya dulu biar nanti ga kaget lihat harga wkwkwk.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }
  if (preference.status === "waiting_payment") {
    return (
      <Card className="border-primary/40 bg-primary/5">
        <CardHeader className="flex-row items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">Pencarian disetujui</CardTitle>
            <CardDescription>
              Pilih paket untuk mulai mencocokkan loker.
            </CardDescription>
          </div>
          <Button asChild size="sm">
            <Link to="/plans">Pilih paket</Link>
          </Button>
        </CardHeader>
      </Card>
    );
  }
  return null;
}
