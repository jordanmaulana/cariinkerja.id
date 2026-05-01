import { useEffect, useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSetAtom } from "jotai";

import { ApiError } from "@/lib/api";
import { googleSignIn } from "@/lib/auth";
import { tokenAtom, userAtom } from "@/state/atoms";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

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
    <main className="mx-auto max-w-sm p-8 space-y-6">
      <h1 className="text-2xl font-bold">Sign in</h1>
      <p className="text-sm text-muted-foreground">
        Use your Google account to continue. New accounts are created
        automatically.
      </p>
      <div ref={buttonRef} className="flex justify-center" />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </main>
  );
}
