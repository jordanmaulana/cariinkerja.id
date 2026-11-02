#!/usr/bin/env bash
# Deploy latest main: pull, build, migrate, swap containers.
set -euo pipefail
cd "$(dirname "$0")"

dc() { docker compose --env-file .env.docker "$@"; }

git pull --ff-only origin main

# Build while old containers keep serving.
dc build

# Migrate with the new image before swapping. One-off container, no ports published.
# ROLE=migrate makes the entrypoint skip its own migrate + collectstatic.
dc run --rm -e ROLE=migrate backend uv run manage.py migrate --noinput

# Recreate changed containers; wait for health checks.
if ! dc up -d --wait; then
  docker inspect --format '{{range .State.Health.Log}}{{.Output}}{{end}}' "$(dc ps -q backend)"
  exit 1
fi

# Remove only this project's dangling images (old builds this deploy replaced).
docker image prune -f --filter "label=com.docker.compose.project=$(dc config | sed -n 's/^name: //p')"
dc ps
