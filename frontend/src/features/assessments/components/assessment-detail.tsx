import { ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScoreGauge } from "@/features/assessments/components/score-gauge";
import { SkillGapCard } from "@/features/assessments/components/skill-gap-card";
import { getActionsForStatus } from "@/features/assessments/actions";
import type {
  Assessment,
  AssessmentStatus,
} from "@/features/assessments/types";
import { JOB_TYPE_LABEL, REMOTE_LABEL } from "@/features/jobs/consts";

type Props = {
  assessment: Assessment;
  isPending: boolean;
  onAction: (next: AssessmentStatus) => void;
};

export function AssessmentDetail({ assessment, isPending, onAction }: Props) {
  const { job, preference, status, score, verdict, created_on } = assessment;
  const actions = getActionsForStatus(status);
  const created = new Date(created_on).toLocaleDateString("id-ID", {
    day: "2-digit",
    month: "short",
  });

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 space-y-2">
              <CardTitle className="text-xl">{job.title}</CardTitle>
              <CardDescription>
                <span className="font-medium text-foreground">
                  {job.company ?? "—"}
                </span>
                {" · "}
                {job.location ?? "—"}
                {" · "}
                {job.job_type ? JOB_TYPE_LABEL[job.job_type] : "—"}
                {" · "}
                {job.remote_option ? REMOTE_LABEL[job.remote_option] : "—"}
              </CardDescription>
              <div className="text-xs text-muted-foreground">
                Dicocokkan dengan{" "}
                <span className="font-medium text-foreground">
                  {preference.title ?? "—"}
                </span>
                {" · Dinilai "}
                {created}
              </div>
            </div>
            <ScoreGauge value={score} />
          </div>
        </CardHeader>
        <CardContent className="border-t pt-5">
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild variant="outline" size="sm">
              <a href={job.url} target="_blank" rel="noreferrer">
                <ExternalLink className="size-3.5" />
                Lihat loker asli
              </a>
            </Button>
            {actions.length === 0 ? (
              <span className="text-xs text-muted-foreground">
                Status final — tidak ada aksi lebih lanjut.
              </span>
            ) : (
              actions.map((a) => (
                <Button
                  key={a.next}
                  size="sm"
                  variant={a.variant ?? "default"}
                  disabled={isPending}
                  onClick={() => onAction(a.next)}
                >
                  {a.label}
                </Button>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {verdict && (
        <Card>
          <CardHeader>
            <CardTitle>Penilaian</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm leading-relaxed">
              {verdict}
            </p>
          </CardContent>
        </Card>
      )}

      <SkillGapCard assessment={assessment} />
    </div>
  );
}
