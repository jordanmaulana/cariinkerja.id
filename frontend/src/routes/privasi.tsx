// DRAFT for founder review against UU PDP — not legal advice.
import { createFileRoute } from "@tanstack/react-router";

import { LegalPage, LegalSection } from "@/features/legal/components/legal-page";
import { SUPPORT_EMAIL, SUPPORT_WHATSAPP } from "@/features/legal/consts";

export const Route = createFileRoute("/privasi")({
  head: () => ({ meta: [{ title: "Kebijakan Privasi — cariinkerja.id" }] }),
  component: PrivacyPage,
});

function PrivacyPage() {
  return (
    <LegalPage
      title="Kebijakan Privasi"
      intro={
        <p>
          Halaman ini jelasin data apa aja yang kami simpan waktu kamu pakai
          cariinkerja.id, buat apa, dan siapa aja yang ikut memprosesnya. Kami
          nggak jual datamu ke siapa pun.
        </p>
      }
    >
      <LegalSection title="Data yang kami kumpulkan">
        <ul>
          <li>
            <strong>Dari akun Google</strong> waktu kamu sign in: alamat email
            dan nama.
          </li>
          <li>
            <strong>Dari formulir onboarding</strong>: nama lengkap, nomor HP,
            URL LinkedIn, bio (opsional), dan pencarianmu (job title, tipe
            kerja, opsi remote).
          </li>
          <li>
            <strong>Dari profil LinkedIn</strong> yang URL-nya kamu kasih: isi
            profil seperti pengalaman kerja, pendidikan, skill, bagian About,
            dan status Open to Work. Kami simpan versi mentahnya dan versi yang
            udah dirapikan AI.
          </li>
          <li>
            <strong>Hasil penilaian</strong>: skor 0–100, skill yang cocok dan
            yang masih kurang (skill gap), verdict, dan status loker yang kamu
            tandai (dilihat, apply, ditolak, diterima).
          </li>
          <li>
            <strong>Data langganan</strong>: paket, nominal yang dibayar, status
            dan ID transaksi dari Mayar. Data kartu atau rekeningmu nggak pernah
            sampai ke kami, semuanya diproses langsung di Mayar.
          </li>
          <li>
            <strong>Data penggunaan situs</strong>: halaman yang kamu buka dan
            rekaman sesi (lihat bagian di bawah).
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="Buat apa datanya dipakai">
        <ul>
          <li>Menilai kecocokan tiap loker baru dengan profilmu.</li>
          <li>
            Ngecek apakah profil LinkedIn-mu cukup lengkap buat dinilai, sebelum
            kamu bisa berlangganan.
          </li>
          <li>
            Ngirim email ringkasan kalau ada loker baru dengan skor 80 ke atas.
          </li>
          <li>Memproses pembayaran dan mengaktifkan langgananmu.</li>
          <li>Bantu kamu kalau kamu menghubungi admin.</li>
          <li>Memperbaiki produk dan mencegah penyalahgunaan.</li>
        </ul>
      </LegalSection>

      <LegalSection title="Pihak ketiga yang ikut memproses datamu">
        <p>
          Biar layanan ini jalan, sebagian datamu diproses oleh layanan pihak
          ketiga berikut:
        </p>
        <ul>
          <li>
            <strong>Google</strong>: untuk sign in.
          </li>
          <li>
            <strong>Apify</strong>: untuk mengambil isi profil LinkedIn dari URL
            yang kamu kasih.
          </li>
          <li>
            <strong>OpenAI</strong>: penyedia AI yang merapikan profilmu dan
            menilai tiap loker. Isi profilmu dan teks loker dikirim ke sini
            untuk diproses.
          </li>
          <li>
            <strong>TypeSafe AI</strong>: untuk ngecek apakah job title yang kamu
            isi masuk akal. Yang dikirim cuma job title-nya.
          </li>
          <li>
            <strong>Mayar</strong>: untuk pembayaran. Nama, email, dan nomor HP
            kamu dikirim ke Mayar buat bikin tagihan.
          </li>
          <li>
            <strong>Umami</strong> (kami jalankan di server sendiri): untuk
            analytics dan rekaman sesi.
          </li>
          <li>
            <strong>Discord</strong>: notifikasi internal ke admin waktu ada
            pencarian baru, isinya nama profil dan job title-nya.
          </li>
          <li>
            <strong>Layanan email (SMTP)</strong>: untuk ngirim email ringkasan
            ke kamu.
          </li>
        </ul>
        <p>
          Job title yang kamu cari juga dipakai sebagai kata kunci pencarian di
          job board. Data pribadimu nggak ikut dikirim ke job board.
        </p>
      </LegalSection>

      <LegalSection title="Rekaman sesi">
        <p>
          Kami pakai Umami buat ngitung kunjungan dan merekam sesi di situs ini:
          halaman yang dibuka, klik, scroll, dan perpindahan halaman. Tujuannya
          biar kami tahu bagian mana yang bikin bingung terus bisa diperbaiki.
          Rekaman ini cuma dilihat sama admin.
        </p>
      </LegalSection>

      <LegalSection title="Penyimpanan">
        <p>
          Datamu disimpan di server kami selama akunmu masih ada. Token login
          disimpan di browser-mu (local storage) dan hilang waktu kamu logout.
          Kalau kamu minta akunmu dihapus, data profil, pencarian, dan hasil
          penilaianmu ikut kami hapus.
        </p>
      </LegalSection>

      <LegalSection title="Hak kamu">
        <p>
          Sesuai UU Pelindungan Data Pribadi (UU No. 27 Tahun 2022), kamu berhak
          minta akses ke datamu, minta salinannya, memperbaiki data yang salah,
          menarik persetujuan, dan minta datamu dihapus.
        </p>
        <p>
          Caranya: hubungi admin lewat{" "}
          <a href={SUPPORT_WHATSAPP} target="_blank" rel="noopener noreferrer">
            WhatsApp
          </a>{" "}
          atau email ke <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
        </p>
      </LegalSection>

      <LegalSection title="Kode terbuka">
        <p>
          Kode cariinkerja.id terbuka (AGPL-3.0) di{" "}
          <a
            href="https://github.com/jordanmaulana/cariinkerja.id"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          , jadi siapa pun bisa ngecek sendiri gimana datamu diproses.
        </p>
      </LegalSection>

      <LegalSection title="Perubahan kebijakan">
        <p>
          Kalau kebijakan ini berubah, tanggal di atas ikut kami perbarui. Cek
          halaman ini sesekali ya.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
