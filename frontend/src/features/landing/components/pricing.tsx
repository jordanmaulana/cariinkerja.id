import { Link } from "@tanstack/react-router";
import { ArrowRight, Check, Wallet } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePublicPlans } from "@/features/billing/hooks";
import { durationLabel, formatRupiah } from "@/features/billing/utils";

const INCLUDED = [
  "Loker baru dicari tiap pagi",
  "Skor 0–100, skill gap, dan verdict buat tiap loker",
  "Email kalau ada loker skor 80+",
];

export function Pricing() {
  const { data, isLoading, isError } = usePublicPlans();
  const plans = data ?? [];

  return (
    <section id="harga" className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
      <div className="mx-auto max-w-2xl text-center">
        <Badge variant="outline" className="mb-4">
          <Wallet className="size-3" />
          Harga
        </Badge>
        <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          Pilih paket, tanpa kontrak.
        </h2>
        <p className="mt-3 text-muted-foreground">
          Paketnya cuma beda di jumlah pencarian (job title) yang bisa jalan
          bareng. Nggak diperpanjang otomatis.
        </p>
      </div>

      {isLoading ? (
        <div className="mx-auto mt-10 grid max-w-3xl gap-4 sm:grid-cols-2">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-64 w-full rounded-xl" />
          ))}
        </div>
      ) : isError || plans.length === 0 ? (
        <div className="mt-8 text-center">
          <Button asChild variant="outline">
            <Link to="/login">Lihat paket setelah sign in</Link>
          </Button>
        </div>
      ) : (
        <div className="mx-auto mt-10 grid max-w-3xl gap-4 sm:grid-cols-2">
          {plans.map((plan) => (
            <Card key={plan.id} className="shadow-lg">
              <CardContent className="flex h-full flex-col gap-5 px-6 py-6">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    {plan.name}
                  </p>
                  <p className="mt-2">
                    <span className="font-heading text-4xl font-semibold tabular-nums">
                      {formatRupiah(plan.price)}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {" "}
                      / {durationLabel(plan.duration_days)}
                    </span>
                  </p>
                  <p className="mt-1 text-sm font-medium">
                    {plan.preference_limit} pencarian
                  </p>
                </div>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {INCLUDED.map((item) => (
                    <li key={item} className="flex gap-2">
                      <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                      {item}
                    </li>
                  ))}
                </ul>
                <Button asChild className="mt-auto">
                  <Link to="/login">
                    Mulai sekarang
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <p className="mx-auto mt-6 max-w-xl text-center text-sm text-muted-foreground">
        Status Open to Work di LinkedIn-mu nyala? Paket termurah otomatis
        dipotong Rp 15.000. Lagi nyari kerja serius, harusnya nggak bayar harga
        penuh.
      </p>
    </section>
  );
}
