// DRAFT for founder review against UU PDP — not legal advice.
import { Link, createFileRoute } from "@tanstack/react-router";

import { LegalPage, LegalSection } from "@/features/legal/components/legal-page";
import { SUPPORT_EMAIL, SUPPORT_WHATSAPP } from "@/features/legal/consts";

export const Route = createFileRoute("/syarat")({
  head: () => ({ meta: [{ title: "Syarat & Ketentuan — cariinkerja.id" }] }),
  component: TermsPage,
});

function TermsPage() {
  return (
    <LegalPage
      title="Syarat & Ketentuan"
      intro={
        <p>
          Dengan sign in dan pakai cariinkerja.id, kamu setuju sama syarat di
          bawah ini. Bacanya pelan-pelan ya, nggak panjang kok.
        </p>
      }
    >
      <LegalSection title="Layanannya apa">
        <p>
          cariinkerja.id nyariin loker dari berbagai job board tiap hari, terus
          AI menilai tiap loker terhadap profil LinkedIn-mu: skor 0–100, skill
          yang cocok, skill gap, dan verdict singkat.
        </p>
        <p>
          Skor itu perkiraan AI, bukan keputusan HR. Kami bukan agen penyalur
          kerja dan <strong>nggak menjamin kamu dapet kerja, interview, atau
          dibales recruiter</strong>. Kami bantu nemuin loker yang cocok, apply
          dan interview-nya tetap di kamu.
        </p>
      </LegalSection>

      <LegalSection title="Akun dan data kamu">
        <ul>
          <li>Sign in pakai akun Google.</li>
          <li>
            Isi data dengan jujur, dan pakai profil LinkedIn milikmu sendiri.
            Jangan pakai profil orang lain.
          </li>
          <li>
            Kualitas penilaian bergantung sama isi LinkedIn-mu. Kalau profilmu
            terlalu kosong, kami bisa menolak pembayaran sampai profilnya
            dilengkapi.
          </li>
          <li>
            Cara kami mengolah datamu ada di{" "}
            <Link to="/privasi">Kebijakan Privasi</Link>.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="Berbayar, tanpa trial">
        <ul>
          <li>
            Layanan ini berbayar dan nggak ada trial. Pencarian loker baru mulai
            jalan setelah pembayaranmu berhasil.
          </li>
          <li>
            Harga dan lama langganan mengikuti paket yang tampil waktu kamu
            checkout. Paket menentukan berapa pencarian (job title) yang bisa
            jalan bareng.
          </li>
          <li>
            Langganan nggak diperpanjang otomatis. Kalau masa langganan habis,
            pencarianmu berhenti sampai kamu berlangganan lagi.
          </li>
          <li>
            Kalau status Open to Work di LinkedIn-mu nyala, paket termurah
            otomatis dapat potongan harga. Paket lain dan upgrade tetap harga
            normal.
          </li>
          <li>Pembayaran diproses lewat Mayar.</li>
        </ul>
      </LegalSection>

      <LegalSection title="Upgrade dan downgrade">
        <ul>
          <li>
            Upgrade: kamu bayar harga penuh paket baru, dan sisa nilai paket
            lamamu diubah jadi hari bonus di paket baru. Sisa nilai itu nggak
            dikembalikan sebagai uang atau saldo.
          </li>
          <li>
            Downgrade nggak tersedia. Tunggu paketmu habis dulu, baru pilih
            paket yang lebih kecil.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="Pencarian dan status loker">
        <ul>
          <li>
            Kalau kamu mengubah pencarian yang lagi jalan, pencariannya berhenti
            dulu dan dicek admin sebelum jalan lagi.
          </li>
          <li>Pencarian cuma bisa dihapus selama belum dibayar.</li>
          <li>
            Status loker cuma bisa maju (Baru → Sudah dilihat → Sudah dilamar →
            Dapat tawaran), dan kamu bisa tandai Ditolak kapan aja. Nggak ada
            loker yang hilang: semua loker, termasuk yang kamu tolak, tetap bisa
            kamu lihat lewat filter status di daftar loker.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="Tentang lokernya">
        <ul>
          <li>
            Loker milik job board atau perusahaan aslinya. Tombol apply
            membawamu ke sumber aslinya.
          </li>
          <li>
            Kami nggak bisa jamin isi loker selalu akurat atau masih buka. Selalu
            cek ulang di sumbernya sebelum apply.
          </li>
          <li>
            Job board kadang memblokir crawler, jadi jumlah loker per hari bisa
            naik turun.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="Yang nggak boleh">
        <ul>
          <li>Pakai data palsu atau profil LinkedIn orang lain.</li>
          <li>
            Menyalahgunakan layanan, misalnya membebani server atau mengambil
            data secara otomatis dari aplikasi ini.
          </li>
          <li>Menjual ulang akses akunmu ke orang lain.</li>
        </ul>
        <p>Kalau dilanggar, kami bisa menghentikan akunmu.</p>
      </LegalSection>

      <LegalSection title="Batas tanggung jawab">
        <p>
          Layanan ini disediakan apa adanya. Kami berusaha supaya crawler dan
          penilaian jalan tiap hari, tapi kami nggak bertanggung jawab atas
          keputusan yang kamu ambil berdasarkan skor, atau atas proses rekrutmen
          di perusahaan mana pun.
        </p>
      </LegalSection>

      <LegalSection title="Kode terbuka">
        <p>
          Kode cariinkerja.id dirilis dengan lisensi AGPL-3.0 di{" "}
          <a
            href="https://github.com/jordanmaulana/cariinkerja.id"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          . Lisensi itu berlaku untuk kodenya, sedangkan syarat di halaman ini
          berlaku untuk layanan di cariinkerja.id.
        </p>
      </LegalSection>

      <LegalSection title="Perubahan dan kontak">
        <p>
          Syarat ini bisa berubah, dan tanggal di atas ikut kami perbarui.
          Syarat ini tunduk pada hukum Republik Indonesia.
        </p>
        <p>
          Ada pertanyaan? Hubungi admin lewat{" "}
          <a href={SUPPORT_WHATSAPP} target="_blank" rel="noopener noreferrer">
            WhatsApp
          </a>{" "}
          atau email ke <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
