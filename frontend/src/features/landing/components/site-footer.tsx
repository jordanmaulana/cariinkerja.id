import { LogoLockup } from "@/components/brand/logo-mark";

export function SiteFooter() {
  return (
    <footer className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-col items-start justify-between gap-4 text-xs text-muted-foreground sm:flex-row sm:items-center">
        <LogoLockup />
        <p>
          Dibuat untuk pencari kerja Indonesia. © 2026 cariinkerja.id ·{" "}
          <a
            href="https://github.com/jordanmaulana/cariinkerja.id"
            target="_blank"
            rel="noopener noreferrer"
            className="underline-offset-2 hover:underline"
          >
            Source
          </a>
        </p>
      </div>
    </footer>
  );
}
