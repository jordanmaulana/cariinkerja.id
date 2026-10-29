import { createFileRoute } from "@tanstack/react-router";
import { ExternalLink } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { JOB_SOURCES } from "@/features/compliance/sources";
import { SiteFooter } from "@/features/landing/components/site-footer";
import { SiteHeader } from "@/features/landing/components/site-header";

export const Route = createFileRoute("/compliance")({
  head: () => ({ meta: [{ title: "Compliance — cariinkerja.id" }] }),
  component: CompliancePage,
});

function CompliancePage() {
  return (
    <main className="relative min-h-svh w-full bg-background text-foreground">
      <SiteHeader />
      <section className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-3xl font-semibold tracking-tight">Compliance</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Sumber lowongan di bawah ini secara resmi mengizinkan lowongannya
          ditampilkan di portal lain. Berikut pernyataan dan syaratnya — klik
          tautan untuk membaca langsung dari sumbernya.
        </p>
        <div className="mt-8 space-y-4">
          {JOB_SOURCES.map((source) => (
            <Card key={source.name}>
              <CardHeader>
                <CardTitle>{source.name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {source.permissions.map((p) => (
                  <div key={p.url} className="space-y-1.5">
                    <blockquote className="border-l-2 pl-3 text-sm">
                      {p.statement}
                    </blockquote>
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-start gap-1 break-all pl-3 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                    >
                      <ExternalLink className="mt-0.5 size-3 shrink-0" />
                      {p.url}
                    </a>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}
