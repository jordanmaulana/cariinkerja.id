import { Skeleton } from "@/components/ui/skeleton";
import { usePublicPlans } from "@/features/billing/hooks";
import { durationLabel, formatRupiah } from "@/features/billing/utils";

// Read-only price list for logged-out visitors. Renders nothing on error so
// the login page never breaks because of it.
export function PlanPreviewList() {
  const { data, isLoading } = usePublicPlans();

  if (!isLoading && !data?.length) return null;

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold tracking-tight">Paket</p>
      <ul className="rounded-md border border-border divide-y divide-border">
        {isLoading
          ? [1, 2].map((i) => (
              <li key={i} className="px-3 py-2.5">
                <Skeleton className="h-9 w-full" />
              </li>
            ))
          : data?.map((plan) => (
              <li
                key={plan.id}
                className="flex items-center justify-between gap-4 px-3 py-2.5"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">{plan.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {plan.preference_limit} pencarian
                  </p>
                </div>
                <p className="shrink-0 text-right">
                  <span className="text-sm font-semibold tabular-nums">
                    {formatRupiah(plan.effective_price)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {" "}
                    / {durationLabel(plan.duration_days)}
                  </span>
                </p>
              </li>
            ))}
      </ul>
    </div>
  );
}
