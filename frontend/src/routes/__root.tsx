import { Suspense, lazy, useCallback, useEffect } from "react"
import {
  Outlet,
  createRootRoute,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router"
import { useQueryClient } from "@tanstack/react-query"
import { useAtom } from "jotai"

import { AppShell } from "@/components/app-shell"
import { ApiError } from "@/lib/api"
import { me } from "@/lib/auth"
import { useUserEvents, type UserEvent } from "@/lib/realtime"
import { tokenAtom, userAtom } from "@/state/atoms"

const TanStackRouterDevtools = import.meta.env.DEV
  ? lazy(() =>
    import("@tanstack/router-devtools").then((m) => ({
      default: m.TanStackRouterDevtools,
    })),
  )
  : () => null
const ReactQueryDevtools = import.meta.env.DEV
  ? lazy(() =>
    import("@tanstack/react-query-devtools").then((m) => ({
      default: m.ReactQueryDevtools,
    })),
  )
  : () => null

const PUBLIC_PATHS = new Set(["/login"])
const FULL_BLEED_PATHS = new Set([...PUBLIC_PATHS, "/onboarding"])

function useRealtimeSync() {
  const queryClient = useQueryClient()
  const handler = useCallback(
    (e: UserEvent) => {
      switch (e.event) {
        case "assessment.status_changed":
          if (typeof e.assessment_id === "string") {
            queryClient.invalidateQueries({
              queryKey: ["assessment", e.assessment_id],
            })
          }
          queryClient.invalidateQueries({ queryKey: ["assessments"] })
          break
        case "subscription.activated":
          queryClient.invalidateQueries({ queryKey: ["subscription", "me"] })
          queryClient.invalidateQueries({ queryKey: ["plans"] })
          queryClient.invalidateQueries({ queryKey: ["payment-gate"] })
          break
        case "preference.status_changed":
          queryClient.invalidateQueries({ queryKey: ["preferences"] })
          if (typeof e.preference_id === "string") {
            queryClient.invalidateQueries({
              queryKey: ["preference", e.preference_id],
            })
          }
          queryClient.invalidateQueries({ queryKey: ["payment-gate"] })
          break
      }
    },
    [queryClient],
  )
  useUserEvents(handler)
}

function AuthGate() {
  const [token, setToken] = useAtom(tokenAtom)
  const [user, setUser] = useAtom(userAtom)
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  useRealtimeSync()

  useEffect(() => {
    if (!token || user) return
    let cancelled = false
    me()
      .then((u) => {
        if (!cancelled) setUser(u)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 401) {
          setToken(null)
          setUser(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [token, user, setToken, setUser])

  useEffect(() => {
    if (!token) {
      if (!PUBLIC_PATHS.has(pathname)) {
        navigate({ to: "/login" })
      }
      return
    }
    if (!user) return
    if (!user.onboarded && pathname !== "/onboarding") {
      navigate({ to: "/onboarding" })
      return
    }
    if (user.onboarded && (PUBLIC_PATHS.has(pathname) || pathname === "/onboarding")) {
      navigate({ to: "/dashboard" })
    }
  }, [token, user, pathname, navigate])

  if (!token || !user || FULL_BLEED_PATHS.has(pathname)) {
    return <Outlet />
  }
  return <AppShell />
}

export const Route = createRootRoute({
  component: () => (
    <>
      <AuthGate />
      <Suspense fallback={null}>
        <TanStackRouterDevtools />
        <ReactQueryDevtools initialIsOpen={false} />
      </Suspense>
    </>
  ),
})
