import { Link } from "@tanstack/react-router";
import { ArrowRight, Check, Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ScoreGauge } from "@/features/assessments/components/score-gauge";
import {
  ASSESSMENT_MOCK,
  HERO_HARD_GAP,
  HERO_HARD_MATCH,
  HERO_SCORE,
} from "@/features/landing/consts";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border/60">
      <HeroBackground />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 py-16 lg:grid-cols-2 lg:gap-16 lg:py-24">
        <div className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-4 motion-safe:duration-700">
          <Badge variant="outline" className="mb-5">
            <Sparkles className="size-3" />
            Pencocokan loker bertenaga AI
          </Badge>
          <h1 className="font-heading text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
            Cariin kamu loker yang cocok,
            <span className="text-muted-foreground">
              {" "}
              biar kamu ga capek cari sendiri.
            </span>
          </h1>
          <p className="mt-5 max-w-lg text-base text-muted-foreground sm:text-lg">
            Set preferensimu sekali. Tiap hari kami ambilin loker baru, AI nilai
            kecocokannya, dan tunjukin skill apa yang masih kurang.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link to="/login">
                Mulai sekarang
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <a href="#features">Lihat fitur</a>
            </Button>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Sign in pake Google. Akun otomatis dibuat — ga perlu daftar manual.
          </p>
        </div>
        <div className="relative">
          <div
            aria-hidden
            className="pointer-events-none absolute -inset-8 -z-10 rounded-[3rem] bg-gradient-to-br from-primary/10 via-transparent to-primary/5 blur-2xl motion-safe:animate-pulse"
            style={{ animationDuration: "6s" }}
          />
          <HeroAssessmentCard />
        </div>
      </div>
    </section>
  );
}

function HeroBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]"
      style={{
        backgroundImage:
          "radial-gradient(circle at 1px 1px, color-mix(in oklch, var(--border) 100%, transparent) 1px, transparent 0)",
        backgroundSize: "20px 20px",
      }}
    />
  );
}

function HeroAssessmentCard() {
  return (
    <Card className="relative shadow-xl motion-safe:animate-in motion-safe:fade-in motion-safe:zoom-in-95 motion-safe:duration-700">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Penilaian
            </div>
            <div className="mt-1 truncate text-lg font-semibold leading-tight">
              {ASSESSMENT_MOCK.job}
            </div>
            <div className="mt-0.5 truncate text-sm text-muted-foreground">
              {ASSESSMENT_MOCK.company} · {ASSESSMENT_MOCK.location}
            </div>
          </div>
          <ScoreGauge value={HERO_SCORE} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{ASSESSMENT_MOCK.verdict}</p>
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Hard skill
          </div>
          <div className="flex flex-wrap gap-1.5">
            {HERO_HARD_MATCH.map((s, i) => (
              <Badge
                key={s}
                variant="secondary"
                className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-500"
                style={{
                  animationDelay: `${300 + i * 120}ms`,
                  animationFillMode: "backwards",
                }}
              >
                <Check className="size-3" />
                {s}
              </Badge>
            ))}
            {HERO_HARD_GAP.map((s, i) => (
              <Badge
                key={s}
                variant="destructive"
                className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-500"
                style={{
                  animationDelay: `${300 + (HERO_HARD_MATCH.length + i) * 120}ms`,
                  animationFillMode: "backwards",
                }}
              >
                <X className="size-3" />
                {s}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
