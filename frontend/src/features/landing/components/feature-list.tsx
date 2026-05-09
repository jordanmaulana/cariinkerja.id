import {
  Gauge,
  Search,
  Sparkles,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  AssessmentCardMock,
  PreferenceFormMock,
  SkillGapMock,
  StatsMock,
} from "@/features/landing/components/feature-mocks";
import { useInView } from "@/features/landing/hooks";
import { cn } from "@/lib/utils";

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
    body: "Set role, full-time atau freelance, remote atau on-site. Crawler tiap hari ngambilin loker baru sesuai filtermu.",
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

export function FeatureList() {
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
