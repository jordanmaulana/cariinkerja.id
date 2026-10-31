import { ChevronDown, CircleHelp } from "lucide-react";

import { Badge } from "@/components/ui/badge";

type Item = { q: string; a: string };

const ITEMS: Item[] = [
  {
    q: "Kenapa nggak ada trial?",
    a: "Dulu sempat ada trial. Nah, ternyata banyak yang ngisi job title asal kayak \"Coba kerja\", atau nempel link LinkedIn orang lain. Validasi itu gak ada ujungnya, jadi sekarang langsung berbayar. Sebagai gantinya, kami nolak pembayaran kalau profil LinkedIn-mu belum cukup lengkap buat dinilai.",
  },
  {
    q: "Kenapa harus LinkedIn?",
    a: "AI-nya menilai tiap loker berdasarkan isi LinkedIn-mu: pengalaman, skill, dan About. Makin lengkap dan jujur profilmu, makin akurat skornya. LinkedIn kosong = penilaian jelek.",
  },
  {
    q: "Lokernya dari mana aja?",
    a: "Dari berbagai job board: Indeed, JobStreet, LinkedIn, Himalayas, Jobicy, Workable, dan Remote OK. Kamu nggak perlu milih, satu pencarian otomatis dicari di semuanya.",
  },
  {
    q: "Skornya dihitung gimana?",
    a: "Loker yang jelas nggak nyambung dibuang dulu. Sisanya dinilai 0–100 terhadap profilmu, lengkap sama skill yang cocok, skill gap, dan verdict singkat. Kalau tipe kerja atau opsi remote-nya nggak sesuai preferensimu, skornya dibatasi rendah dan alasannya ditulis.",
  },
  {
    q: "Ada diskon?",
    a: "Ada. Kalau status Open to Work di LinkedIn-mu nyala, paket termurah otomatis dipotong Rp 15.000. Paket lain dan upgrade tetap harga normal.",
  },
  {
    q: "Pasti dapet kerja?",
    a: "Nggak ada yang bisa jamin itu, termasuk kami. cariinkerja.id bantu kamu fokus ke loker yang cocok, tapi apply dan interview-nya tetap di kamu.",
  },
  {
    q: "Harus langganan sekarang?",
    a: "Nggak harus. Kalau keuanganmu lagi berat, fokus cari kerja sendiri dulu sampai bisa napas lega ya. Kami serius soal ini.",
  },
];

export function Faq() {
  return (
    <section id="faq" className="border-t border-border/60 bg-muted/20">
      <div className="mx-auto max-w-3xl px-6 py-16 lg:py-20">
        <div className="text-center">
          <Badge variant="outline" className="mb-4">
            <CircleHelp className="size-3" />
            FAQ
          </Badge>
          <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
            Yang sering ditanyain
          </h2>
        </div>
        <div className="mt-10 divide-y divide-border rounded-xl border border-border bg-card">
          {ITEMS.map((item) => (
            <details key={item.q} className="group px-5 py-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left font-medium [&::-webkit-details-marker]:hidden">
                {item.q}
                <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {item.a}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
