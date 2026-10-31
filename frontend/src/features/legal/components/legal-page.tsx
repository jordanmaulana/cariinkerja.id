import type { ReactNode } from "react";

import { SiteFooter } from "@/features/landing/components/site-footer";
import { SiteHeader } from "@/features/landing/components/site-header";
import { LEGAL_LAST_UPDATED } from "@/features/legal/consts";

export function LegalPage({
  title,
  intro,
  children,
}: {
  title: string;
  intro: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="relative min-h-svh w-full bg-background text-foreground">
      <SiteHeader />
      <article className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 text-xs text-muted-foreground">
          Terakhir diperbarui: {LEGAL_LAST_UPDATED}
        </p>
        <div className="mt-4 text-sm leading-relaxed text-muted-foreground">
          {intro}
        </div>
        <div className="mt-10 space-y-10">{children}</div>
      </article>
      <SiteFooter />
    </main>
  );
}

export function LegalSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-foreground/90 [&_a]:underline [&_a]:underline-offset-2 [&_li]:pl-1 [&_ul]:list-disc [&_ul]:space-y-1.5 [&_ul]:pl-5">
        {children}
      </div>
    </section>
  );
}
