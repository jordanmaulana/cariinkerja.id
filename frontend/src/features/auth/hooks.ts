import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";

import { ApiError } from "@/lib/api";
import { getProfile, submitOnboarding } from "@/features/auth/api";
import type { OnboardingPayload } from "@/features/auth/components/onboarding-form";
import { userAtom } from "@/features/auth/state";

export function useProfilePrefill() {
  const [initialFullName, setInitialFullName] = useState("");
  const [initialPhone, setInitialPhone] = useState("");

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

  return { initialFullName, initialPhone };
}

export function useOnboardingSubmit() {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const setUser = useSetAtom(userAtom);
  const navigate = useNavigate();

  async function submit(payload: OnboardingPayload) {
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

  return { submit, submitting, error };
}
