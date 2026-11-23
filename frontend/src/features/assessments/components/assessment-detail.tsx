import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScoreGauge } from "@/features/assessments/components/score-gauge";
import { SkillGapCard } from "@/features/assessments/components/skill-gap-card";
import { SourceCredit } from "@/features/assessments/components/source-credit";
import { STATUS_LABEL, STATUS_ORDER } from "@/features/assessments/consts";
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
              {job.is_expired && (
                <Badge variant="destructive" title="Lowongan ini udah lewat batas waktunya di sumber">
                  Kedaluwarsa
                </Badge>
              )}
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
                <SourceCredit job={job} className="before:content-['_·_']" />
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
            <Select
              value={status}
              disabled={isPending}
              onValueChange={(v) => onAction(v as AssessmentStatus)}
            >
              <SelectTrigger aria-label="Ubah status" className="h-8 w-44 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_ORDER.map((s) => (
                  <SelectItem key={s} value={s}>
                    {STATUS_LABEL[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
