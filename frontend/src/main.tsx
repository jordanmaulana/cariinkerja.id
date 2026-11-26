import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { Provider as JotaiProvider } from "jotai";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import { routeTree } from "./routeTree.gen";
import { queryClient } from "@/app/query-client";
import "./styles.css";

// No DSN (local dev) = SDK stays off. userInfo/httpBodies off: no IP, and
// CV text posted to the API never rides along on an error.
Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  dataCollection: { userInfo: false, httpBodies: [] },
});

const router = createRouter({ routeTree, context: { queryClient } });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

createRoot(document.getElementById("root")!, {
  onUncaughtError: Sentry.reactErrorHandler(),
  onCaughtError: Sentry.reactErrorHandler(),
  onRecoverableError: Sentry.reactErrorHandler(),
}).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <JotaiProvider>
        <RouterProvider router={router} />
        <ToastContainer
          position="top-right"
          autoClose={4000}
          newestOnTop
          closeOnClick
          pauseOnHover
          hideProgressBar={false}
        />
      </JotaiProvider>
    </QueryClientProvider>
  </StrictMode>,
);
