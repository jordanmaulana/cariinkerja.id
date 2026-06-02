import { Badge } from "@/components/ui/badge";

// Keep these Q&As in sync with the FAQPage JSON-LD in index.html —
// Google requires the structured data to match the visible text.
const FAQS: { q: string; a: string }[] = [
  {
    q: "Gimana cara kerja pencocokan loker AI di cariinkerja.id?",
    a: "Kamu set preferensi sekali — role, tipe kerja, remote atau on-site. Tiap hari kami ambilin loker baru yang cocok, lalu AI nilai kecocokannya sama profilmu.",
  },
  {
    q: "Apa itu skor kecocokan dan skill gap?",
    a: "Skor kecocokan itu angka 0–100 yang nunjukin seberapa nyambung loker sama profilmu. Skill gap nunjukin hard skill dan soft skill apa yang masih kurang buat loker itu.",
  },
  {
    q: "Apakah ada versi gratis?",
    a: "Ada. Kamu bisa coba crawl pertama gratis buat ngeliat hasil penilaiannya sebelum berlangganan.",
  },
  {
    q: "Sumber lokernya dari mana?",
    a: "Kami ngambil loker dari Indeed, Jobstreet, Glints, terus dinilai otomatis pakai AI.",
  },
];

export function Faq() {
  return (
    <section id="faq" className="mx-auto max-w-6xl px-6 py-20 lg:py-28">
      <div className="mb-12 max-w-2xl">
        <Badge variant="outline" className="mb-4">
          FAQ
        </Badge>
        <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          Pertanyaan yang sering ditanya
        </h2>
        <p className="mt-3 text-muted-foreground">
          Hal-hal yang biasanya kamu pengen tau soal pencocokan loker AI.
        </p>
      </div>
      <dl className="divide-y divide-border/60 border-y border-border/60">
        {FAQS.map((item) => (
          <div key={item.q} className="py-6">
            <dt className="font-heading text-lg font-semibold tracking-tight">
              {item.q}
            </dt>
            <dd className="mt-2 max-w-2xl text-muted-foreground">{item.a}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
