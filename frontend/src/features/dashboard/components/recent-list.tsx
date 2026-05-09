import { Link } from "@tanstack/react-router";

import { Badge } from "@/components/ui/badge";
import type { Assessment } from "@/features/assessments/types";

export function RecentList({ rows }: { rows: Assessment[] }) {
  if (rows.length === 0) {
    return (
      <div className="px-6 py-4 text-sm text-muted-foreground">
        Belum ada penilaian.
      </div>
    );
  }
  return (
    <ul className="divide-y">
      {rows.map((row) => (
        <li key={row.id}>
          <Link
            to="/assessments/$id"
            params={{ id: row.id }}
            className="flex items-center justify-between gap-4 px-6 py-3 transition-colors hover:bg-muted/50"
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">
                {row.job.title}
              </div>
              <div className="truncate text-xs text-muted-foreground">
                {row.job.company || "—"}
                {row.job.location ? ` · ${row.job.location}` : ""}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span className="text-sm tabular-nums">{row.score}</span>
              <Badge variant="outline" className="capitalize">
                {row.status}
              </Badge>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
