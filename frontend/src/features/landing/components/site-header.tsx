import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";

import { LogoLockup } from "@/components/brand/logo-mark";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";

function GithubMark({ className }: { className?: string }) {
  return (
    <svg
      role="img"
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="currentColor"
      className={className}
    >
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56 0-.28-.01-1.02-.02-2-3.2.69-3.88-1.54-3.88-1.54-.52-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 5.78 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.58.24 2.75.12 3.04.74.81 1.18 1.84 1.18 3.1 0 4.43-2.7 5.41-5.27 5.69.41.36.78 1.07.78 2.16 0 1.56-.01 2.81-.01 3.19 0 .31.21.68.8.56C20.22 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  );
}

function LinkedinMark({ className }: { className?: string }) {
  return (
    <svg
      role="img"
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="currentColor"
      className={className}
    >
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.94v5.67H9.36V9h3.41v1.56h.05c.47-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12ZM7.12 20.45H3.56V9h3.56v11.45ZM22.23 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.46c.98 0 1.77-.77 1.77-1.72V1.72C24 .77 23.21 0 22.23 0Z" />
    </svg>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <LogoLockup />
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="icon-sm" aria-label="Lihat di GitHub">
            <a
              href="https://github.com/jordanmaulana/cariinkerja.id"
              target="_blank"
              rel="noopener noreferrer"
            >
              <GithubMark className="size-4" />
            </a>
          </Button>
          <Button asChild variant="ghost" size="icon-sm" aria-label="LinkedIn Jordan Maulana">
            <a
              href="https://www.linkedin.com/in/jordan-maulana/"
              target="_blank"
              rel="noopener noreferrer"
            >
              <LinkedinMark className="size-4" />
            </a>
          </Button>
          <ThemeToggle />
          <Button asChild size="sm">
            <Link to="/login">
              Masuk
              <ArrowRight className="size-3.5" />
            </Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
