import { useEffect, useRef } from "react";
import { Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useAtom } from "jotai";
import { toast } from "react-toastify";

import { AppShell } from "@/components/layout/app-shell";
import { useRealtimeQueryInvalidation } from "@/app/realtime";
import { ApiError } from "@/lib/api";
import { me } from "@/features/auth/api";
import { tokenAtom, userAtom } from "@/features/auth/state";

const PUBLIC_PATHS = new Set(["/", "/login"]);
const FULL_BLEED_PATHS = new Set([...PUBLIC_PATHS, "/onboarding"]);

export function AuthGate() {
  const [token, setToken] = useAtom(tokenAtom);
  const [user, setUser] = useAtom(userAtom);
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const sessionExpiredFiredRef = useRef(false);
  const onboardingNudgeFiredRef = useRef(false);

  useRealtimeQueryInvalidation();

  useEffect(() => {
    if (!token || user) return;
    let cancelled = false;
    me()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          if (!sessionExpiredFiredRef.current) {
            sessionExpiredFiredRef.current = true;
            toast.warning("Sesi kamu sudah berakhir. Silakan masuk lagi.");
          }
          setToken(null);
          setUser(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, user, setToken, setUser]);

  useEffect(() => {
    if (!token) {
      if (!PUBLIC_PATHS.has(pathname)) {
        navigate({ to: "/login" });
      }
      return;
    }
    if (!user) return;
    if (!user.onboarded && pathname !== "/onboarding") {
      if (!onboardingNudgeFiredRef.current) {
        onboardingNudgeFiredRef.current = true;
        toast.info("Lengkapi profilmu dulu sebelum lanjut.");
      }
      navigate({ to: "/onboarding" });
      return;
    }
    if (user.onboarded && (PUBLIC_PATHS.has(pathname) || pathname === "/onboarding")) {
      navigate({ to: "/dashboard" });
    }
  }, [token, user, pathname, navigate]);

  if (!token || !user || FULL_BLEED_PATHS.has(pathname)) {
    return <Outlet />;
  }
  return <AppShell />;
}
