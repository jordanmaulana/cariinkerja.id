import { useEffect, useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";
import { Briefcase, Search, Sparkles } from "lucide-react";

import { LogoLockup } from "@/components/logo-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { googleSignIn } from "@/lib/auth";
import { tokenAtom, userAtom } from "@/state/atoms";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

const FEATURES = [
  {
    icon: Search,
    title: "Set up a Finder",
    body: "Save your preferences and the listing URLs you'd browse on Indeed or JobStreet.",
  },
  {
    icon: Sparkles,
    title: "AI scores every match",
    body: "Skor kecocokan, hard/soft skill match, dan gap analysis di setiap lowongan.",
  },
  {
    icon: Briefcase,
    title: "Lihat yang layak dilamar",
    body: "A ranked list of Available Jobs — updated each visit, no doomscrolling.",
  },
] as const;

function LoginPage() {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const setToken = useSetAtom(tokenAtom);
  const setUser = useSetAtom(userAtom);
  const navigate = useNavigate();

  useEffect(() => {
    if (!CLIENT_ID) {
      setError("Google sign-in is not configured. Set VITE_GOOGLE_CLIENT_ID.");
      return;
    }
    let cancelled = false;
    let attempts = 0;
    const tryInit = () => {
      if (cancelled) return;
      const gid = window.google?.accounts?.id;
      if (!gid || !buttonRef.current) {
        if (attempts++ < 50) setTimeout(tryInit, 100);
        return;
      }
      gid.initialize({
        client_id: CLIENT_ID,
        callback: async ({ credential }) => {
          setError(null);
          try {
            const res = await googleSignIn(credential);
            setToken(res.token);
            setUser(res.user);
            navigate({ to: res.user.onboarded ? "/" : "/onboarding" });
          } catch (err) {
            const msg =
              err instanceof ApiError
                ? err.message
                : "Sign-in failed. Try again.";
            setError(msg);
          }
        },
      });
      gid.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        width: 320,
      });
    };
    tryInit();
    return () => {
      cancelled = true;
    };
  }, [navigate, setToken, setUser]);

  return (
    <main className="relative min-h-svh w-full grid lg:grid-cols-2">
      <div className="absolute top-4 right-4 z-10">
        <ThemeToggle />
      </div>
      <section className="hidden lg:flex flex-col justify-between p-12 border-r border-border bg-muted/30 relative overflow-hidden">
        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, color-mix(in oklch, var(--border) 100%, transparent) 1px, transparent 0)",
            backgroundSize: "20px 20px",
          }}
        />
        <div className="relative">
          <LogoLockup />
        </div>
        <div className="relative">
          <h2 className="font-heading text-3xl xl:text-4xl font-semibold tracking-tight leading-tight">
            Pekerjaan yang cocok, bukan sekadar banyak.
          </h2>
          <p className="mt-3 text-muted-foreground text-base max-w-md">
            We crawl listings, score the match, and rank the openings worth
            your time.
          </p>
          <ul className="mt-10 space-y-6">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <li key={title} className="flex gap-4 items-start">
                <div className="size-9 shrink-0 rounded-md border border-border bg-card grid place-items-center">
                  <Icon className="size-4" aria-hidden />
                </div>
                <div>
                  <p className="text-sm font-medium">{title}</p>
                  <p className="text-sm text-muted-foreground">{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-muted-foreground">
          Dibuat untuk pencari kerja Indonesia. © 2026 cariinkerja.id
        </p>
      </section>

      <section className="flex items-center justify-center p-6 sm:p-10 relative">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-6 flex items-center gap-2 justify-center">
            <LogoLockup />
          </div>
          <Card className="w-full shadow-sm">
            <CardHeader>
              <h1 className="text-2xl font-heading font-semibold tracking-tight">
                Welcome back
              </h1>
              <CardDescription>
                Sign in to manage your Finders and review matched roles.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5 pt-2">
              <div
                ref={buttonRef}
                className="flex justify-center min-h-[44px]"
              />
              {error && (
                <div
                  role="alert"
                  className="text-sm rounded-md border border-destructive/30 bg-destructive/5 text-destructive px-3 py-2"
                >
                  {error}
                </div>
              )}
              <p className="text-xs text-muted-foreground text-center">
                Belum punya akun? Otomatis dibuat saat kamu sign in.
              </p>
            </CardContent>
            <CardFooter className="justify-center text-xs">
              By continuing you agree to our Terms and Privacy Policy.
            </CardFooter>
          </Card>
        </div>
      </section>
    </main>
  );
}
