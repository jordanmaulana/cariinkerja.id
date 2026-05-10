import { useEffect, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { googleSignIn } from "@/features/auth/api";
import { tokenAtom, userAtom } from "@/features/auth/state";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

export function GoogleSignInCard() {
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
        <div ref={buttonRef} className="flex justify-center min-h-[44px]" />
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
  );
}
