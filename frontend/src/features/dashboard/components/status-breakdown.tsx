import { STATUS_LABEL, STATUS_ORDER } from "@/features/assessments/consts";
import type { AssessmentStatus } from "@/features/assessments/types";

type Props = {
  byStatus: Record<AssessmentStatus, number>;
  total: number;
};

export function StatusBreakdown({ byStatus, total }: Props) {
  return (
    <ul className="space-y-3">
      {STATUS_ORDER.map((s) => {
        const count = byStatus[s] ?? 0;
        const pct = total === 0 ? 0 : Math.round((count / total) * 100);
        return (
          <li key={s} className="space-y-1.5">
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted-foreground">{STATUS_LABEL[s]}</span>
              <span className="tabular-nums">
                {count}
                <span className="ml-2 text-xs text-muted-foreground">
                  {pct}%
                </span>
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-foreground/80"
                style={{ width: `${pct}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
