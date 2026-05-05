import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { getProfile, submitOnboarding } from "@/lib/auth";
import { JOB_TYPES, REMOTE_OPTIONS } from "@/lib/consts";
import type { JobType, RemoteOption } from "@/lib/consts";
import { userAtom } from "@/state/atoms";

export const Route = createFileRoute("/onboarding")({
  component: OnboardingPage,
});

function OnboardingPage() {
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");

  useEffect(() => {
    let cancelled = false;
    getProfile()
      .then((p) => {
        if (cancelled) return;
        const prefill = p.full_name || p.suggested_full_name || "";
        if (prefill) setFullName(prefill);
        if (p.phone) setPhone(p.phone);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [bio, setBio] = useState("");
  const [title, setTitle] = useState("");
  const [jobType, setJobType] = useState<JobType>(JOB_TYPES[0].value);
  const [remoteOption, setRemoteOption] = useState<RemoteOption>(
    REMOTE_OPTIONS[0].value,
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const setUser = useSetAtom(userAtom);
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await submitOnboarding({
        full_name: fullName,
        phone,
        linkedin_url: linkedinUrl,
        bio: bio || undefined,
        title,
        job_type: jobType,
        remote_option: remoteOption,
      });
      setUser((prev) =>
        prev ? { ...prev, full_name: fullName, onboarded: true } : prev,
      );
      navigate({ to: "/" });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Gagal menyimpan. Coba lagi.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Ceritain dikit tentang kamu</h1>
        <p className="text-sm text-muted-foreground">
          Isi profil dan Pencarian pertamamu buat mulai. Nomor HP wajib biar
          nanti kita bisa proses pembayaran langgananmu — di sini kamu belum
          ditagih apa-apa.
        </p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <fieldset className="space-y-4">
          <legend className="text-sm font-semibold">Profil</legend>
          <div className="space-y-1">
            <label htmlFor="full_name" className="text-sm font-medium">
              Nama lengkap
            </label>
            <input
              id="full_name"
              required
              autoFocus
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="phone" className="text-sm font-medium">
              Nomor HP
            </label>
            <input
              id="phone"
              type="tel"
              required
              placeholder="08xxxxxxxxxx"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
            <p className="text-xs text-muted-foreground">
              Dipakai pas kamu langganan nanti. Sekarang kamu belum ditagih.
            </p>
          </div>
          <div className="space-y-1">
            <label htmlFor="linkedin_url" className="text-sm font-medium">
              URL LinkedIn
            </label>
            <input
              id="linkedin_url"
              type="url"
              required
              placeholder="https://linkedin.com/in/..."
              value={linkedinUrl}
              onChange={(e) => setLinkedinUrl(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
            <p className="text-xs text-muted-foreground">
              Kami ambil LinkedIn-mu buat verifikasi profil dan menyesuaikan
              kecocokan loker.
            </p>
          </div>
          <div className="space-y-1">
            <label htmlFor="bio" className="text-sm font-medium">
              Bio
            </label>
            <textarea
              id="bio"
              rows={3}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
          </div>
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="text-sm font-semibold">Pencarian pertama</legend>
          <div className="space-y-1">
            <label htmlFor="title" className="text-sm font-medium">
              Judul pekerjaan
            </label>
            <input
              id="title"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded border px-3 py-2"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="job_type" className="text-sm font-medium">
              Tipe pekerjaan
            </label>
            <select
              id="job_type"
              value={jobType}
              onChange={(e) => setJobType(e.target.value as JobType)}
              className="w-full rounded border px-3 py-2"
            >
              {JOB_TYPES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label htmlFor="remote_option" className="text-sm font-medium">
              Opsi remote
            </label>
            <select
              id="remote_option"
              value={remoteOption}
              onChange={(e) => setRemoteOption(e.target.value as RemoteOption)}
              className="w-full rounded border px-3 py-2"
            >
              {REMOTE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </fieldset>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Menyimpan…" : "Selesaikan onboarding"}
        </Button>
      </form>
    </main>
  );
}
