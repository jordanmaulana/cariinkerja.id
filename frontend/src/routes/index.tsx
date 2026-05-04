import { useEffect, useRef, useState } from "react";
import { Link, createFileRoute } from "@tanstack/react-router";
import {
  ArrowRight,
  Briefcase,
  Check,
  Gauge,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  X,
  type LucideIcon,
} from "lucide-react";

import { LogoLockup } from "@/components/logo-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  component: WelcomePage,
});

const HERO_SCORE = 87;
const HERO_HARD_MATCH = ["React", "TypeScript", "Tailwind"] as const;
const HERO_HARD_GAP = ["GraphQL"] as const;

const ASSESSMENT_MOCK = {
  job: "Frontend Engineer",
  company: "Tokopedia",
  location: "Jakarta",
  verdict:
    "Cocok banget. Stack React + TS-mu nyambung. Sentuh GraphQL dikit lagi udah aman.",
  hardMatch: ["React", "TypeScript", "Tailwind", "REST API"],
  hardGap: ["GraphQL", "Kubernetes"],
} as const;

const SKILL_GROUPS = [
  {
    label: "Hard skills",
    match: ["React", "TypeScript", "Tailwind"],
    gap: ["GraphQL", "Kubernetes"],
  },
  {
    label: "Soft skills",
    match: ["Komunikasi", "Ownership"],
    gap: ["Public speaking"],
  },
] as const;

const STAT_TILES: { label: string; value: string; icon: LucideIcon }[] = [
  { label: "Loker dinilai", value: "142", icon: Briefcase },
  { label: "Rata-rata skor", value: "78", icon: Target },
  { label: "Minggu ini", value: "23", icon: TrendingUp },
  { label: "Skor tertinggi", value: "94", icon: Sparkles },
];

const BAR_CHART = [42, 58, 71, 65, 80, 73, 88];

type Feature = {
  num: string;
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  body: string;
  mock: (show: boolean) => React.ReactNode;
};

const FEATURES: Feature[] = [
  {
    num: "01",
    icon: Search,
    eyebrow: "Preferensi",
    title: "Atur preferensimu sekali, kerjain pencariannya buat kamu.",
    body: "Set role, full-time atau freelance, remote atau on-site, terus tempel URL listing favoritmu. Crawler tiap hari ngambilin loker baru sesuai filtermu.",
    mock: () => <PreferenceFormMock />,
  },
  {
    num: "02",
    icon: Gauge,
    eyebrow: "Skor kecocokan",
    title: "AI ngasih skor 0–100 buat tiap loker, biar kamu ga nebak-nebak.",
    body: "Profil + preferensimu dibanding deskripsi loker pake LLM. Hasilnya skor, plus penjelasan singkat kenapa cocok atau nggak.",
    mock: () => <AssessmentCardMock />,
  },
  {
    num: "03",
    icon: Sparkles,
    eyebrow: "Skill gap",
    title: "Tau persis skill apa yang masih kurang per loker.",
    body: "Bukan cuma skor — kamu liat hard skill & soft skill mana yang nyambung dan mana yang masih bolong. Bahan upgrade-an yang konkret.",
    mock: () => <SkillGapMock />,
  },
  {
    num: "04",
    icon: TrendingUp,
    eyebrow: "Statistik",
    title: "Pantau aktivitas pencarianmu, biar tau kapan harus istirahat.",
    body: "Berapa loker yang udah dinilai, rata-rata skor, momentum mingguan. Buat refleksi, bukan flexing.",
    mock: (show) => <StatsMock show={show} />,
  },
];

function WelcomePage() {
  return (
    <main className="relative min-h-svh w-full bg-background text-foreground">
      <SiteHeader />
      <Hero />
      <FeatureList />
      <BottomCta />
      <SiteFooter />
    </main>
  );
}

function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <LogoLockup />
        <div className="flex items-center gap-2">
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

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border/60">
      <HeroBackground />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 py-16 lg:grid-cols-2 lg:gap-16 lg:py-24">
        <div className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-4 motion-safe:duration-700">
          <Badge variant="outline" className="mb-5">
            <Sparkles className="size-3" />
            AI-powered job matcher
          </Badge>
          <h1 className="font-heading text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
            Cariin kamu loker yang cocok,
            <span className="text-muted-foreground"> biar kamu ga capek cari sendiri.</span>
          </h1>
          <p className="mt-5 max-w-lg text-base text-muted-foreground sm:text-lg">
            Set preferensimu sekali. Tiap hari kami ambilin loker baru, AI nilai
            kecocokannya, dan tunjukin skill apa yang masih kurang.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link to="/login">
                Mulai gratis
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
              Assessment
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
            Hard skills
          </div>
          <div className="flex flex-wrap gap-1.5">
            {HERO_HARD_MATCH.map((s, i) => (
              <Badge
                key={s}
                variant="secondary"
                className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-500"
                style={{ animationDelay: `${300 + i * 120}ms`, animationFillMode: "backwards" }}
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

function ScoreGauge({ value }: { value: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setN(value);
      return;
    }
    const start = performance.now();
    const dur = 1200;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(value * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  const r = 42;
  const c = 2 * Math.PI * r;
  const offset = c - (n / 100) * c;

  return (
    <div className="relative grid size-24 shrink-0 place-items-center">
      <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-90">
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke="var(--muted)"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke="var(--primary)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="text-center">
        <div className="font-heading text-2xl font-semibold leading-none tabular-nums">
          {n}
        </div>
        <div className="mt-1 text-[9px] uppercase tracking-wider text-muted-foreground">
          / 100
        </div>
      </div>
    </div>
  );
}

function FeatureList() {
  return (
    <section id="features" className="mx-auto max-w-6xl px-6 py-20 lg:py-28">
      <div className="mb-16 max-w-2xl">
        <Badge variant="outline" className="mb-4">
          Fitur
        </Badge>
        <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          Yang kamu dapet kalo pake cariinkerja.id
        </h2>
        <p className="mt-3 text-muted-foreground">
          Empat hal yang ngebantu kamu cari kerja tanpa burnout.
        </p>
      </div>
      <div className="space-y-24 lg:space-y-32">
        {FEATURES.map((f, i) => (
          <FeatureSection key={f.num} feature={f} reverse={i % 2 === 1} />
        ))}
      </div>
    </section>
  );
}

function FeatureSection({
  feature,
  reverse,
}: {
  feature: Feature;
  reverse: boolean;
}) {
  const { ref, show } = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={cn(
        "grid items-center gap-10 lg:grid-cols-2 lg:gap-16",
        "motion-safe:transition-all motion-safe:duration-700 motion-safe:ease-out",
        !show && "motion-safe:translate-y-6 motion-safe:opacity-0",
      )}
    >
      <div className={cn(reverse && "lg:order-2")}>
        <div className="mb-4 inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <span className="grid size-7 place-items-center rounded-full border border-border bg-card">
            <feature.icon className="size-3.5" />
          </span>
          <span className="tabular-nums">{feature.num}</span>
          <span className="text-border">·</span>
          <span>{feature.eyebrow}</span>
        </div>
        <h3 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
          {feature.title}
        </h3>
        <p className="mt-3 max-w-md text-muted-foreground">{feature.body}</p>
      </div>
      <div className={cn(reverse && "lg:order-1")}>{feature.mock(show)}</div>
    </div>
  );
}

function PreferenceFormMock() {
  return (
    <Card className="shadow-lg">
      <CardHeader>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Preference
        </div>
        <div className="mt-1 text-base font-semibold">Senior React Engineer</div>
      </CardHeader>
      <CardContent className="space-y-3.5">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Job type" value="Full-time" />
          <Field label="Remote" value="Remote" />
        </div>
        <div>
          <FieldLabel>Source</FieldLabel>
          <div className="mt-1 flex gap-1.5">
            <SourcePill active>Indeed</SourcePill>
            <SourcePill>JobStreet</SourcePill>
          </div>
        </div>
        <div>
          <FieldLabel>Crawl URL</FieldLabel>
          <div className="mt-1 truncate rounded-md border bg-muted/40 px-2.5 py-1.5 font-mono text-xs">
            https://id.indeed.com/jobs?q=react+engineer
          </div>
        </div>
        <div className="flex items-center justify-between border-t pt-3">
          <span className="text-xs text-muted-foreground">Status</span>
          <Badge>
            <span className="relative mr-0.5 inline-flex size-1.5">
              <span className="absolute inset-0 animate-ping rounded-full bg-primary-foreground/60" />
              <span className="relative size-1.5 rounded-full bg-primary-foreground" />
            </span>
            Running
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function AssessmentCardMock() {
  return (
    <Card className="shadow-lg">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Assessment
            </div>
            <div className="mt-1 truncate text-base font-semibold leading-tight">
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
        <div>
          <FieldLabel>Hard skills</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {ASSESSMENT_MOCK.hardMatch.map((s) => (
              <Badge key={s} variant="secondary">
                <Check className="size-3" />
                {s}
              </Badge>
            ))}
            {ASSESSMENT_MOCK.hardGap.map((s) => (
              <Badge key={s} variant="destructive">
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

function SkillGapMock() {
  return (
    <Card className="shadow-lg">
      <CardHeader>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Skill gap
        </div>
        <div className="mt-1 text-base font-semibold">Apa yang udah & belum</div>
      </CardHeader>
      <CardContent className="space-y-5">
        {SKILL_GROUPS.map((g) => (
          <div key={g.label}>
            <FieldLabel>{g.label}</FieldLabel>
            <ul className="mt-2 space-y-1.5">
              {g.match.map((s) => (
                <li key={s} className="flex items-center gap-2 text-sm">
                  <span className="grid size-5 place-items-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <Check className="size-3" />
                  </span>
                  {s}
                </li>
              ))}
              {g.gap.map((s) => (
                <li
                  key={s}
                  className="flex items-center gap-2 text-sm text-muted-foreground"
                >
                  <span className="grid size-5 place-items-center rounded-full bg-destructive/10 text-destructive">
                    <X className="size-3" />
                  </span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function StatsMock({ show }: { show: boolean }) {
  return (
    <Card className="shadow-lg">
      <CardHeader>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Statistik
        </div>
        <div className="mt-1 text-base font-semibold">30 hari terakhir</div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-2">
          {STAT_TILES.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-md border bg-muted/30 p-3">
              <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                <Icon className="size-3" />
                {label}
              </div>
              <div className="mt-1 font-heading text-xl font-semibold tabular-nums">
                {value}
              </div>
            </div>
          ))}
        </div>
        <div>
          <FieldLabel>Aktivitas mingguan</FieldLabel>
          <div className="mt-2 flex h-20 items-end gap-1.5">
            {BAR_CHART.map((v, i) => (
              <div
                key={i}
                className="flex-1 rounded-sm bg-primary/70"
                style={{
                  height: show ? `${v}%` : "0%",
                  transition: `height 700ms cubic-bezier(0.22, 1, 0.36, 1) ${i * 60}ms`,
                }}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <div className="mt-1 rounded-md border bg-muted/40 px-2.5 py-1.5 text-sm">
        {value}
      </div>
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
      {children}
    </div>
  );
}

function SourcePill({
  children,
  active,
}: {
  children: React.ReactNode;
  active?: boolean;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs",
        active
          ? "border-primary/40 bg-primary/10 text-foreground"
          : "border-border bg-card text-muted-foreground",
      )}
    >
      {children}
    </span>
  );
}

function BottomCta() {
  return (
    <section className="border-y border-border/60 bg-muted/30">
      <div className="mx-auto max-w-6xl px-6 py-16 text-center">
        <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          Udah cukup capek scroll loker manual?
        </h2>
        <p className="mx-auto mt-3 max-w-md text-muted-foreground">
          Sign in sekali, set preferensi, terus biarin AI yang nyari. Kamu fokus
          aja ke skill upgrade.
        </p>
        <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg">
            <Link to="/login">
              Mulai sekarang
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-col items-start justify-between gap-4 text-xs text-muted-foreground sm:flex-row sm:items-center">
        <LogoLockup />
        <p>Dibuat untuk pencari kerja Indonesia. © 2026 cariinkerja.id</p>
      </div>
    </footer>
  );
}

function useInView<T extends HTMLElement>(
  options?: IntersectionObserverInit,
): { ref: React.RefObject<T | null>; show: boolean } {
  const ref = useRef<T | null>(null);
  const [show, setShow] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setShow(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShow(true);
            io.disconnect();
            break;
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -10% 0px", ...options },
    );
    io.observe(node);
    return () => io.disconnect();
  }, [options]);
  return { ref, show };
}
