import type { AssessmentJob } from "@/features/assessments/types";

// Sources whose API terms require visible credit with a link back.
const CREDITED: Record<string, string> = {
  jobicy: "Jobicy",
  himalayas: "Himalayas",
};

type Props = {
  job: AssessmentJob;
  // false inside an element that is already a link (no nested <a>).
  link?: boolean;
  className?: string;
};

export function SourceCredit({ job, link = true, className }: Props) {
  const name = job.source ? CREDITED[job.source] : undefined;
  if (!name) return null;
  return (
    <span className={className}>
      via{" "}
      {link ? (
        // No noreferrer: the source should see the referral.
        <a
          href={job.url}
          target="_blank"
          rel="noopener"
          className="underline underline-offset-2 hover:text-foreground"
        >
          {name}
        </a>
      ) : (
        name
      )}
    </span>
  );
}
