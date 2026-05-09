import { createFileRoute } from "@tanstack/react-router";

import { OnboardingForm } from "@/features/auth/components/onboarding-form";
import {
  useOnboardingSubmit,
  useProfilePrefill,
} from "@/features/auth/hooks";

export const Route = createFileRoute("/onboarding")({
  component: OnboardingPage,
});

function OnboardingPage() {
  const { initialFullName, initialPhone } = useProfilePrefill();
  const { submit, submitting, error } = useOnboardingSubmit();

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
        onSubmit={submit}
      />
    </main>
  );
}
