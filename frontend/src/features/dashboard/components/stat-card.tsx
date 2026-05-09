import { Card, CardContent } from "@/components/ui/card";

type Props = {
  label: string;
  value: number;
  hint?: string;
  suffix?: string;
};

export function StatCard({ label, value, hint, suffix }: Props) {
  return (
    <Card>
      <CardContent className="px-5 py-4">
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className="mt-1 flex items-baseline gap-1">
          <span className="text-3xl font-semibold tabular-nums">{value}</span>
          {suffix && (
            <span className="text-sm text-muted-foreground">{suffix}</span>
          )}
        </div>
        {hint && (
          <div className="mt-1 text-xs text-muted-foreground">{hint}</div>
        )}
      </CardContent>
    </Card>
  );
}
