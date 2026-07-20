import {
  IndeedMark,
  JobStreetMark,
  LinkedinMark,
} from "@/features/landing/components/brand-marks";
import { useInView } from "@/features/landing/hooks";
import { cn } from "@/lib/utils";

type Source = {
  name: string;
  Mark: (props: { className?: string }) => React.ReactNode;
  note?: string;
};

const SOURCES: Source[] = [
  { name: "LinkedIn SEA", Mark: LinkedinMark, note: "Southeast Asia" },
  { name: "LinkedIn EMEA", Mark: LinkedinMark, note: "Europe Middle East Africa" },
  { name: "Indeed", Mark: IndeedMark },
  { name: "JobStreet", Mark: JobStreetMark },
];

export function SourceStrip() {
  const { ref, show } = useInView<HTMLDivElement>();

  return (
    <section className="border-b border-border/60">
      <div
        ref={ref}
        className={cn(
          "mx-auto max-w-6xl px-6 py-10 text-center",
          "motion-safe:transition-all motion-safe:duration-700 motion-safe:ease-out",
          !show && "motion-safe:translate-y-6 motion-safe:opacity-0",
        )}
      >
        <div className="text-xs uppercase tracking-wider text-muted-foreground">
          Kami ambil loker dari
        </div>
        <div className="mt-6 flex flex-wrap items-start justify-center gap-x-10 gap-y-6">
          {SOURCES.map((source) => (
            <div
              key={source.name}
              className="flex flex-col items-center gap-1 text-muted-foreground transition-colors hover:text-foreground"
            >
              <span className="inline-flex items-center gap-2">
                <source.Mark className="size-5" />
                <span className="text-sm font-medium">{source.name}</span>
              </span>
              {source.note ? (
                <span className="text-[0.625rem] uppercase tracking-wider opacity-70">
                  {source.note}
                </span>
              ) : null}
            </div>
          ))}
        </div>
        <p className="mt-5 text-xs text-muted-foreground">Sumber baru nanti nyusul</p>
      </div>
    </section>
  );
}
