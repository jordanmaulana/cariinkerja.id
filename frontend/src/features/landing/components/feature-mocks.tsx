import { Check, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ScoreGauge } from "@/features/assessments/components/score-gauge";
import {
  ASSESSMENT_MOCK,
  BAR_CHART,
  HERO_SCORE,
  SKILL_GROUPS,
  STAT_TILES,
} from "@/features/landing/consts";

export function PreferenceFormMock() {
  return (
    <Card className="shadow-lg">
      <CardHeader>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Preferensi
        </div>
        <div className="mt-1 text-base font-semibold">Senior React Engineer</div>
      </CardHeader>
      <CardContent className="space-y-3.5">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Tipe pekerjaan" value="Penuh waktu" />
          <Field label="Remote" value="Remote" />
        </div>

        <div className="flex items-center justify-between border-t pt-3">
          <span className="text-xs text-muted-foreground">Status</span>
          <Badge>
            <span className="relative mr-0.5 inline-flex size-1.5">
              <span className="absolute inset-0 animate-ping rounded-full bg-primary-foreground/60" />
              <span className="relative size-1.5 rounded-full bg-primary-foreground" />
            </span>
            Berjalan
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

export function AssessmentCardMock() {
  return (
    <Card className="shadow-lg">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Penilaian
            </div>
            <div className="mt-1 truncate text-base font-semibold leading-tight">
              {ASSESSMENT_MOCK.job}
            </div>
            <div className="mt-0.5 truncate text-sm text-muted-foreground">
              {ASSESSMENT_MOCK.company} · {ASSESSMENT_MOCK.location}
            </div>
          </div>
          <ScoreGauge value={HERO_SCORE} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{ASSESSMENT_MOCK.verdict}</p>
        <div>
          <FieldLabel>Hard skill</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {ASSESSMENT_MOCK.hardMatch.map((s) => (
              <Badge key={s} variant="secondary">
                <Check className="size-3" />
                {s}
              </Badge>
            ))}
            {ASSESSMENT_MOCK.hardGap.map((s) => (
              <Badge key={s} variant="destructive">
                <X className="size-3" />
                {s}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function SkillGapMock() {
  return (
    <Card className="shadow-lg">
      <CardHeader>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Skill gap
        </div>
        <div className="mt-1 text-base font-semibold">Apa yang udah & belum</div>
      </CardHeader>
      <CardContent className="space-y-5">
        {SKILL_GROUPS.map((g) => (
          <div key={g.label}>
            <FieldLabel>{g.label}</FieldLabel>
            <ul className="mt-2 space-y-1.5">
              {g.match.map((s) => (
                <li key={s} className="flex items-center gap-2 text-sm">
                  <span className="grid size-5 place-items-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <Check className="size-3" />
                  </span>
                  {s}
                </li>
              ))}
              {g.gap.map((s) => (
                <li
                  key={s}
                  className="flex items-center gap-2 text-sm text-muted-foreground"
                >
                  <span className="grid size-5 place-items-center rounded-full bg-destructive/10 text-destructive">
                    <X className="size-3" />
                  </span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function StatsMock({ show }: { show: boolean }) {
  return (
    <Card className="shadow-lg">
      <CardHeader>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Statistik
        </div>
        <div className="mt-1 text-base font-semibold">30 hari terakhir</div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-2">
          {STAT_TILES.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-md border bg-muted/30 p-3">
              <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                <Icon className="size-3" />
                {label}
              </div>
              <div className="mt-1 font-heading text-xl font-semibold tabular-nums">
                {value}
              </div>
            </div>
          ))}
        </div>
        <div>
          <FieldLabel>Aktivitas mingguan</FieldLabel>
          <div className="mt-2 flex h-20 items-end gap-1.5">
            {BAR_CHART.map((v, i) => (
              <div
                key={i}
                className="flex-1 rounded-sm bg-primary/70"
                style={{
                  height: show ? `${v}%` : "0%",
                  transition: `height 700ms cubic-bezier(0.22, 1, 0.36, 1) ${i * 60}ms`,
                }}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <div className="mt-1 rounded-md border bg-muted/40 px-2.5 py-1.5 text-sm">
        {value}
      </div>
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
      {children}
    </div>
  );
}
