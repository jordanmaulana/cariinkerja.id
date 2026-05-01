import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  title?: string;
};

export function LogoMark({ className, title = "cariinkerja.id" }: Props) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeWidth={3.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label={title}
      className={cn("size-6", className)}
    >
      <circle cx="24" cy="24" r="20" />
      <circle cx="24" cy="24" r="11" />
      <path
        d="M24 13l1.6 4.4L30 19l-4.4 1.6L24 25l-1.6-4.4L18 19l4.4-1.6Z"
        fill="currentColor"
        stroke="none"
      />
      <path d="M24 17v14M17 24h14" />
    </svg>
  );
}

export function LogoLockup({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <LogoMark className="size-7 text-primary" />
      <span className="font-heading text-lg font-semibold tracking-tight">
        cariinkerja<span className="opacity-60">.id</span>
      </span>
    </div>
  );
}
