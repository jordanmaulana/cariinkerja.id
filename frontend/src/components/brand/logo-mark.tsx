import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  title?: string;
};

export function LogoMark({ className, title = "cariinkerja.id" }: Props) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 240 240"
      fill="none"
      role="img"
      aria-label={title}
      className={cn("size-6", className)}
    >
      <defs>
        <linearGradient id="logoBg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1a1424" />
          <stop offset="100%" stopColor="#050308" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="240" height="240" rx="48" fill="url(#logoBg)" />
      <circle
        cx="120"
        cy="120"
        r="92"
        fill="none"
        stroke="#ffffff"
        strokeOpacity="0.10"
        strokeWidth="12"
      />
      <circle
        cx="120"
        cy="120"
        r="92"
        fill="none"
        stroke="#863bff"
        strokeWidth="12"
        strokeLinecap="round"
        strokeDasharray="531.9 46.3"
        transform="rotate(-90 120 120)"
      />
      <text
        x="120"
        y="156"
        textAnchor="middle"
        fontFamily="'Helvetica Neue', Helvetica, Arial, sans-serif"
        fontWeight="800"
        fontSize="120"
        letterSpacing="-4"
        fill="#ffffff"
      >
        92
      </text>
    </svg>
  );
}

export function LogoLockup({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <LogoMark className="size-7" />
      <span className="font-heading text-lg font-semibold tracking-tight">
        cariinkerja<span className="opacity-60">.id</span>
      </span>
    </div>
  );
}
