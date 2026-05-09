import { Suspense, lazy } from "react";
import { createRootRoute } from "@tanstack/react-router";

import { AuthGate } from "@/features/auth/components/auth-gate";

const TanStackRouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import("@tanstack/router-devtools").then((m) => ({
        default: m.TanStackRouterDevtools,
      })),
    )
  : () => null;
const ReactQueryDevtools = import.meta.env.DEV
  ? lazy(() =>
      import("@tanstack/react-query-devtools").then((m) => ({
        default: m.ReactQueryDevtools,
      })),
    )
  : () => null;

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
});
