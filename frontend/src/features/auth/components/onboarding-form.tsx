import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  JOB_TYPES,
  REMOTE_OPTIONS,
  type JobType,
  type RemoteOption,
} from "@/features/jobs/consts";
import { checkJobTitle } from "@/features/preferences/api";
import { ApiError } from "@/lib/api";

export type OnboardingPayload = {
  full_name: string;
  phone: string;
  linkedin_url: string;
  bio: string;
  title: string;
  job_type: JobType[];
  remote_option: RemoteOption[];
};

type Props = {
  initialFullName?: string;
  initialPhone?: string;
  submitting: boolean;
  error: string | null;
  onSubmit: (payload: OnboardingPayload) => void;
};

export function OnboardingForm({
  initialFullName = "",
  initialPhone = "",
  submitting,
  error,
  onSubmit,
}: Props) {
  // null until the user types, so the async profile prefill shows through.
  const [fullNameEdit, setFullName] = useState<string | null>(null);
  const [phoneEdit, setPhone] = useState<string | null>(null);
  const fullName = fullNameEdit ?? initialFullName;
  const phone = phoneEdit ?? initialPhone;
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [bio, setBio] = useState("");
  const [title, setTitle] = useState("");
  const [jobType, setJobType] = useState<JobType[]>([]);
  const [remoteOption, setRemoteOption] = useState<RemoteOption[]>([]);
  // Last checked title + its error. The error only shows while the input still
  // matches, so editing hides it and a late response can't tag newer text.
  const [titleCheck, setTitleCheck] = useState<{
    title: string;
    error: string | null;
  } | null>(null);
  const titleError =
    titleCheck?.title === title.trim() ? titleCheck.error : null;

  async function checkTitle() {
    const value = title.trim();
    if (!value || titleCheck?.title === value) return;
    try {
      await checkJobTitle(value);
      setTitleCheck({ title: value, error: null });
    } catch (err) {
      // Anything but a 400 verdict fails open; submit re-checks server-side.
      if (err instanceof ApiError && err.status === 400) {
        setTitleCheck({ title: value, error: err.message });
      }
    }
  }

  function toggleJobType(value: JobType, checked: boolean) {
    setJobType((prev) => {
      if (checked) {
        if (prev.includes(value)) return prev;
        return JOB_TYPES.map((o) => o.value).filter(
          (v) => prev.includes(v) || v === value,
        );
      }
      return prev.filter((v) => v !== value);
    });
  }

  function toggleRemoteOption(value: RemoteOption, checked: boolean) {
    setRemoteOption((prev) => {
      if (checked) {
        if (prev.includes(value)) return prev;
        return REMOTE_OPTIONS.map((o) => o.value).filter(
          (v) => prev.includes(v) || v === value,
        );
      }
      return prev.filter((v) => v !== value);
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      full_name: fullName,
      phone,
      linkedin_url: linkedinUrl,
      bio,
      title,
      job_type: jobType,
      remote_option: remoteOption,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
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
          <p className="text-xs text-muted-foreground">
            Tulis posisi kerja kayak kamu lagi cari loker.
            Contoh: "Sales manager", "Guru bahasa Inggris", "UI/UX designer", dsb.
          </p>
          <input
            id="title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={checkTitle}
            aria-invalid={!!titleError}
            aria-describedby={titleError ? "title-error" : undefined}
            className="w-full rounded border px-3 py-2"
          />
          {titleError && (
            <p id="title-error" className="text-xs text-red-600">
              {titleError}
            </p>
          )}
        </div>
        <div className="space-y-2">
          <span className="text-sm font-medium">Tipe pekerjaan</span>
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {JOB_TYPES.map((o) => {
              const id = `onboarding-job-type-${o.value}`;
              const checked = jobType.includes(o.value);
              return (
                <label
                  key={o.value}
                  htmlFor={id}
                  className="inline-flex items-center gap-2 text-sm cursor-pointer select-none"
                >
                  <Checkbox
                    id={id}
                    checked={checked}
                    onCheckedChange={(state) =>
                      toggleJobType(o.value, state === true)
                    }
                  />
                  {o.label}
                </label>
              );
            })}
          </div>
          <p className="text-xs text-muted-foreground">
            Centang yang kamu cari. Kosongin = semua tipe.
          </p>
        </div>
        <div className="space-y-2">
          <span className="text-sm font-medium">Opsi remote</span>
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {REMOTE_OPTIONS.map((o) => {
              const id = `onboarding-remote-${o.value}`;
              const checked = remoteOption.includes(o.value);
              return (
                <label
                  key={o.value}
                  htmlFor={id}
                  className="inline-flex items-center gap-2 text-sm cursor-pointer select-none"
                >
                  <Checkbox
                    id={id}
                    checked={checked}
                    onCheckedChange={(state) =>
                      toggleRemoteOption(o.value, state === true)
                    }
                  />
                  {o.label}
                </label>
              );
            })}
          </div>
          <p className="text-xs text-muted-foreground">
            Centang yang kamu cari. Kosongin = semua opsi.
          </p>
        </div>
      </fieldset>

      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button
        type="submit"
        disabled={submitting || !!titleError}
        className="w-full"
      >
        {submitting ? "Menyimpan…" : "Selesaikan onboarding"}
      </Button>
    </form>
  );
}
