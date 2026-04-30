import { useEffect } from "react";
import {
  Outlet,
  createRootRoute,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/router-devtools";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useAtom } from "jotai";

import { ApiError } from "@/lib/api";
import { me } from "@/lib/auth";
import { tokenAtom, userAtom } from "@/state/atoms";

const PUBLIC_PATHS = new Set(["/login", "/signup"]);

function AuthGate() {
  const [token, setToken] = useAtom(tokenAtom);
  const [user, setUser] = useAtom(userAtom);
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  // Hydrate user from server when we have a token but no cached user.
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
    if (!user) return; // wait until /me resolves
    if (!user.onboarded && pathname !== "/onboarding") {
      navigate({ to: "/onboarding" });
      return;
    }
    if (user.onboarded && (PUBLIC_PATHS.has(pathname) || pathname === "/onboarding")) {
      navigate({ to: "/" });
    }
  }, [token, user, pathname, navigate]);

  return <Outlet />;
}

export const Route = createRootRoute({
  component: () => (
    <>
      <AuthGate />
      <TanStackRouterDevtools />
      <ReactQueryDevtools initialIsOpen={false} />
    </>
  ),
});
