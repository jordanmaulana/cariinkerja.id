import { useEffect, useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";
import { Briefcase, Gauge, Search, Sparkles } from "lucide-react";

import { LogoLockup } from "@/components/logo-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  Card,
  CardContent,
  CardDescription,
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
] as const;

const BEFORE_YOU_BUY = [
  "Pastiin LinkedIn-mu nggak kopong. Jangan cuma nulis education / job experience cuma title doang.",
  "Lengkapi apapun yang bisa dilengkapi di LinkedIn-mu. Tulis semua skills, tulis About yang jujur.",
  "Jangan beli kalo kamu masih financially struggling. Pastiin energimu buat kamu cari kerja dulu sendiri sampe kamu bisa nafas lega.",
] as const;

function LoginPage() {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const setToken = useSetAtom(tokenAtom);
  const setUser = useSetAtom(userAtom);
  const navigate = useNavigate();

  useEffect(() => {
    if (!CLIENT_ID) {
      setError("Google sign-in belum dikonfigurasi. Set VITE_GOOGLE_CLIENT_ID.");
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
                : "Sign in gagal. Coba lagi.";
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
          <div className="mt-8 rounded-md border border-border bg-card/40 p-5 max-w-md">
            <h2 className="text-sm font-semibold tracking-tight">
              Sebelum kamu beli
            </h2>
            <ol className="mt-3 space-y-2 text-sm text-muted-foreground list-decimal list-inside">
              {BEFORE_YOU_BUY.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          </div>
        </div>
        <div className="relative">
          <h2 className="font-heading text-3xl xl:text-4xl font-semibold tracking-tight leading-tight">
            Cariin kamu loker yang cocok, biar kamu ga capek cari sendiri.
          </h2>
          <p className="mt-3 text-muted-foreground text-base max-w-md">
            Manfaatin waktu luangmu buat upgrade skill yang kamu butuhin dari loker yang kamu pilih / yaudah terserah mau tidur kek apalah.
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
                Selamat datang
              </h1>
              <CardDescription>
                Masuk buat liat loker apa aja yang cocok buat kamu.
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

          </Card>
          <div className="mt-6 lg:hidden rounded-md border border-border bg-muted/30 p-5">
            <h2 className="text-sm font-semibold tracking-tight">
              Sebelum kamu beli
            </h2>
            <ol className="mt-3 space-y-2 text-sm text-muted-foreground list-decimal list-inside">
              {BEFORE_YOU_BUY.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          </div>
        </div>
      </section>
    </main>
  );
}
