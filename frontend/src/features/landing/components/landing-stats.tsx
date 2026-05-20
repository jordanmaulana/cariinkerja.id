import {
  Briefcase,
  ClipboardCheck,
  Sparkles,
  TrendingUp,
  UserRound,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { PublicStatBucket, PublicStats } from "@/features/landing/api";
import { useInView, usePublicStats } from "@/features/landing/hooks";
import { cn } from "@/lib/utils";

type Tile = {
  key: keyof PublicStats;
  label: string;
  icon: LucideIcon;
};

const TILES: Tile[] = [
  { key: "profiles", label: "Pencari kerja", icon: UserRound },
  { key: "jobs", label: "Loker", icon: Briefcase },
  { key: "assessments", label: "Assessments", icon: ClipboardCheck },
  { key: "highly_suitable", label: "Highly Suitable Jobs (skor 80+)", icon: TrendingUp },
];

export function LandingStats() {
  const { data, isLoading, isError } = usePublicStats();
  const { ref, show } = useInView<HTMLDivElement>();

  if (isError) return null;

  return (
    <section className="relative overflow-hidden">
      <SectionDots />
      <div
        ref={ref}
        className={cn(
          "relative mx-auto max-w-6xl px-6 py-16 lg:py-20",
          "motion-safe:transition-all motion-safe:duration-700 motion-safe:ease-out",
          !show && "motion-safe:translate-y-6 motion-safe:opacity-0",
        )}
      >
        <div className="mx-auto max-w-2xl text-center">
          <Badge variant="outline" className="mb-4">
            <Sparkles className="size-3" />
            Bukan janji, ini progresnya
          </Badge>
          <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
            Udah jalan, datanya nyata.
          </h2>
          <p className="mt-3 text-muted-foreground">
            Cari & kasih skor sekitar 20 loker setelah registrasi, cari loker tiap hari selama 30 hari buat yang berlangganan.
          </p>
        </div>
        <div className="mt-10 grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
          {TILES.map((tile, i) =>
            isLoading || !data ? (
              <TileSkeleton key={tile.key} />
            ) : (
              <StatTile
                key={tile.key}
                tile={tile}
                bucket={data[tile.key]}
                delay={i * 90}
              />
            ),
          )}
        </div>
      </div>
    </section>
  );
}

function SectionDots() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 opacity-50 [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)]"
      style={{
        backgroundImage:
          "radial-gradient(circle at 1px 1px, color-mix(in oklch, var(--border) 100%, transparent) 1px, transparent 0)",
        backgroundSize: "20px 20px",
      }}
    />
  );
}

function StatTile({
  tile,
  bucket,
  delay,
}: {
  tile: Tile;
  bucket: PublicStatBucket;
  delay: number;
}) {
  const Icon = tile.icon;
  return (
    <Card
      className="shadow-lg transition-shadow hover:shadow-xl motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-3 motion-safe:duration-500"
      style={{ animationDelay: `${delay}ms`, animationFillMode: "backwards" }}
    >
      <CardContent className="px-5 py-5">
        <div className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <span className="grid size-7 place-items-center rounded-full border border-border bg-card">
            <Icon className="size-3.5" />
          </span>
          <span>{tile.label}</span>
        </div>
        <div className="mt-3 font-heading text-4xl font-semibold tabular-nums sm:text-5xl">
          {bucket.total.toLocaleString("id-ID")}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          +{bucket.today.toLocaleString("id-ID")} hari ini
        </div>
      </CardContent>
    </Card>
  );
}

function TileSkeleton() {
  return (
    <Card className="shadow-lg">
      <CardContent className="px-5 py-5">
        <div className="inline-flex items-center gap-2">
          <Skeleton className="size-7 rounded-full" />
          <Skeleton className="h-3 w-28" />
        </div>
        <Skeleton className="mt-4 h-10 w-20" />
        <Skeleton className="mt-2 h-3 w-24" />
      </CardContent>
    </Card>
  );
}
