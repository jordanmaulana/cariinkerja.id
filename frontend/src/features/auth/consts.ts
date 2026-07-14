import { Briefcase, Gauge, Search, Sparkles, type LucideIcon } from "lucide-react";

export const LOGIN_FEATURES: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: Search,
    title: "Atur Preferensimu",
    body: "Set preferensi, mau remote apa on-site, mau full-time apa freelance.",
  },
  {
    icon: Gauge,
    title: "AI ngasih skor kecocokan",
    body: "Deskripsi loker dibanding profil + preferensimu dinilai pake AI, biar kamu tau seberapa cocok kamu sama loker itu.",
  },
  {
    icon: Sparkles,
    title: "Jadi tau skill gaps kamu",
    body: "Per loker kamu bakal bisa tau skill apa aja yang kamu kurang, biar kamu bisa upgrade skill itu.",
  },
  {
    icon: Briefcase,
    title: "Lihat statistikmu",
    body: "Biar kamu ga omong doang apply banyak loker padahal cuma 3. Atau kalo kamu beneran apply banyak, kamu biar tau kamu layak istirahat sebentar.",
  },
];

export const BEFORE_YOU_BUY: string[] = [
  "Pastiin LinkedIn-mu nggak kopong. Jangan cuma nulis education / job experience cuma title doang.",
  "Lengkapi apapun yang bisa dilengkapi di LinkedIn-mu. Tulis semua skills, tulis About yang jujur.",
  "Jangan daftar kalo kamu masih financially struggling. Pastiin energimu buat kamu cari kerja dulu sendiri sampe kamu bisa nafas lega.",
  "Ini layanan berbayar lho ga pake trial."
];
