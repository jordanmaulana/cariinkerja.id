import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import { sentryVitePlugin } from "@sentry/vite-plugin";
import path from "node:path";

// Source maps are built and uploaded only when the token is present, then
// deleted so nginx never serves them. An org token (sntrys_…) carries the
// org slug; SENTRY_ORG overrides it for a user token.
const uploadSourceMaps = Boolean(process.env.SENTRY_AUTH_TOKEN);

export default defineConfig({
  build: { sourcemap: uploadSourceMaps ? "hidden" : false },
  plugins: [
    TanStackRouterVite({ target: "react", autoCodeSplitting: true }),
    react(),
    tailwindcss(),
    sentryVitePlugin({
      project: "cariinkerja-spa",
      disable: !uploadSourceMaps,
      telemetry: false,
      sourcemaps: { filesToDeleteAfterUpload: ["./dist/**/*.map"] },
    }),
  ],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      // Skill Map pages are rendered by Django (frontend/nginx.conf in prod).
      "/skill": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
