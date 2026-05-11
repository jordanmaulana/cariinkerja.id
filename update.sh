#!/usr/bin/env bash
# Zero-downtime deploy.
#
# Prereq (one-time on host):
#   mkdir -p ~/.docker/cli-plugins
#   curl -fsSL https://raw.githubusercontent.com/wowu/docker-rollout/v0.4/docker-rollout \
#     -o ~/.docker/cli-plugins/docker-rollout
#   chmod +x ~/.docker/cli-plugins/docker-rollout
#
# Also: cloudflared tunnel ingress must point at http://backend:8000 and
# http://frontend:3000 (internal Docker DNS), not host:8006 / host:3005.
# CLOUDFLARE_TUNNEL_TOKEN must be set in .env.docker.

set -euo pipefail
cd "$(dirname "$0")"

COMPOSE="docker compose --env-file .env.docker"

echo "==> git pull"
git pull --ff-only

echo "==> build backend + frontend"
$COMPOSE build backend frontend

echo "==> ensure core services up"
$COMPOSE up -d postgres redis cloudflared

echo "==> wait for postgres healthy"
until [ "$($COMPOSE ps -q postgres | xargs -I{} docker inspect -f '{{.State.Health.Status}}' {})" = "healthy" ]; do
  sleep 2
done

echo "==> migrate (one-shot against new image; expand phase)"
$COMPOSE run --rm --no-deps backend uv run manage.py migrate --noinput

echo "==> rollout backend"
docker rollout --env-file .env.docker backend

echo "==> rollout frontend"
docker rollout --env-file .env.docker frontend

echo "==> restart worker (graceful; acks_late redelivers in-flight tasks)"
$COMPOSE up -d --no-deps --build worker

echo "==> restart beat (single-instance; brief scheduling gap is harmless)"
$COMPOSE up -d --no-deps --build beat

echo "==> done"
$COMPOSE ps
