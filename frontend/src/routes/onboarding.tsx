import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";

import { ApiError } from "@/lib/api";
import { getProfile, submitOnboarding } from "@/features/auth/api";
import {
  OnboardingForm,
  type OnboardingPayload,
} from "@/features/auth/components/onboarding-form";
import { userAtom } from "@/features/auth/state";

export const Route = createFileRoute("/onboarding")({
  component: OnboardingPage,
});

function OnboardingPage() {
  const [initialFullName, setInitialFullName] = useState("");
  const [initialPhone, setInitialPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const setUser = useSetAtom(userAtom);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    getProfile()
      .then((p) => {
        if (cancelled) return;
        const prefill = p.full_name || p.suggested_full_name || "";
        if (prefill) setInitialFullName(prefill);
        if (p.phone) setInitialPhone(p.phone);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(payload: OnboardingPayload) {
    setError(null);
    setSubmitting(true);
    try {
      await submitOnboarding({
        full_name: payload.full_name,
        phone: payload.phone,
        linkedin_url: payload.linkedin_url,
        bio: payload.bio || undefined,
        title: payload.title,
        job_type: payload.job_type,
        remote_option: payload.remote_option,
      });
      setUser((prev) =>
        prev ? { ...prev, full_name: payload.full_name, onboarded: true } : prev,
      );
      navigate({ to: "/" });
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "Gagal menyimpan. Coba lagi.";
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
      <OnboardingForm
        initialFullName={initialFullName}
        initialPhone={initialPhone}
        submitting={submitting}
        error={error}
        onSubmit={handleSubmit}
      />
    </main>
  );
}
