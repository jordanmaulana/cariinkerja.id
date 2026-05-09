import { Check, X } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Assessment } from "@/features/assessments/types";

export function SkillGapCard({ assessment }: { assessment: Assessment }) {
  const groups = [
    {
      label: "Hard skill",
      match: assessment.hard_skill_match,
      gap: assessment.hard_skill_gap,
    },
    {
      label: "Soft skill",
      match: assessment.soft_skill_match,
      gap: assessment.soft_skill_gap,
    },
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Skill gap</CardTitle>
        <CardDescription>Apa yang udah & belum</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 sm:grid-cols-2">
        {groups.map((g) => (
          <div key={g.label}>
            <FieldLabel>{g.label}</FieldLabel>
            {g.match.length === 0 && g.gap.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">Belum ada.</p>
            ) : (
              <ul className="mt-2 space-y-1.5">
                {g.match.map((s) => (
                  <li
                    key={`m-${s}`}
                    className="flex items-center gap-2 text-sm"
                  >
                    <span className="grid size-5 place-items-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      <Check className="size-3" />
                    </span>
                    {s}
                  </li>
                ))}
                {g.gap.map((s) => (
                  <li
                    key={`g-${s}`}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <span className="grid size-5 place-items-center rounded-full bg-destructive/10 text-destructive">
                      <X className="size-3" />
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
      {children}
    </div>
  );
}
