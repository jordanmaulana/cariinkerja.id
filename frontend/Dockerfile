FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
ARG VITE_API_URL
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_SENTRY_DSN
ENV VITE_API_URL=$VITE_API_URL \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID \
    VITE_SENTRY_DSN=$VITE_SENTRY_DSN
# Source-map upload token: ARG only (no ENV), so the nginx image never carries it.
# ponytail: it stays in this build stage's cache on the VPS (which already holds
# .env.docker); switch to a BuildKit secret if images ever go to a registry.
ARG SENTRY_AUTH_TOKEN
RUN pnpm run build

# nginx serves the SPA and forwards /skill/ to the backend (see nginx.conf).
FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 3000
