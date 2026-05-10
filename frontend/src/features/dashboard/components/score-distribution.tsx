import { cn } from "@/lib/utils";

const BUCKET_LABELS = ["0–25", "26–50", "51–75", "76–100"] as const;

type Props = {
  buckets: [number, number, number, number];
};

export function ScoreDistribution({ buckets }: Props) {
  const total = buckets.reduce((a, b) => a + b, 0);
  const tones = [
    "bg-foreground/15",
    "bg-foreground/35",
    "bg-foreground/60",
    "bg-foreground/85",
  ];
  return (
    <div className="space-y-3">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
        {buckets.map((count, i) => {
          const pct = total === 0 ? 0 : (count / total) * 100;
          if (pct === 0) return null;
          return (
            <div
              key={i}
              className={cn("h-full", tones[i])}
              style={{ width: `${pct}%` }}
              title={`${BUCKET_LABELS[i]}: ${count}`}
            />
          );
        })}
      </div>
      <ul className="grid grid-cols-2 gap-y-2 text-sm sm:grid-cols-4">
        {buckets.map((count, i) => (
          <li key={i} className="flex items-center gap-2">
            <span className={cn("size-2.5 rounded-sm", tones[i])} />
            <span className="text-muted-foreground">{BUCKET_LABELS[i]}</span>
            <span className="tabular-nums">{count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
