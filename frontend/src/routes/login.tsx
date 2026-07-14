import { createFileRoute } from "@tanstack/react-router";

import { LogoLockup } from "@/components/brand/logo-mark";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { GoogleSignInCard } from "@/features/auth/components/google-sign-in-card";
import { LoginSidePanel } from "@/features/auth/components/login-side-panel";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  return (
    <main className="relative min-h-svh w-full grid lg:grid-cols-2">
      <div className="absolute top-4 right-4 z-10">
        <ThemeToggle />
      </div>
      <LoginSidePanel />
      <section className="flex items-center justify-center p-6 sm:p-10 relative">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-6 flex items-center gap-2 justify-center">
            <LogoLockup />
          </div>
          <GoogleSignInCard />
        </div>
      </section>
    </main>
  );
}
