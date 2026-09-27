import { Suspense, lazy, useEffect } from "react";
import { HeadContent, Link, createRootRoute } from "@tanstack/react-router";

import { LogoMark } from "@/components/brand/logo-mark";
import { Button } from "@/components/ui/button";
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
  // Title only: a per-route description would duplicate index.html's static one.
  head: () => ({ meta: [{ title: "cariinkerja.id — Cariin kamu loker yang cocok" }] }),
  component: () => (
    <>
      <HeadContent />
      <AuthGate />
      <Suspense fallback={null}>
        <TanStackRouterDevtools />
        <ReactQueryDevtools initialIsOpen={false} />
      </Suspense>
    </>
  ),
  notFoundComponent: NotFoundPage,
});

function NotFoundPage() {
  // `serve -s` answers every path with 200, so tell crawlers this is a soft 404.
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => meta.remove();
  }, []);

  return (
    <main className="grid min-h-[70svh] place-items-center px-4 text-center">
      <title>Halaman tidak ditemukan — cariinkerja.id</title>
      <div className="flex flex-col items-center gap-4">
        <LogoMark className="size-12" />
        <p className="text-sm font-medium text-muted-foreground">404</p>
        <h1 className="text-2xl font-semibold">Halaman tidak ditemukan</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Halaman yang kamu cari nggak ada atau sudah dipindah.
        </p>
        <Button asChild>
          <Link to="/">Kembali ke beranda</Link>
        </Button>
      </div>
    </main>
  );
}
