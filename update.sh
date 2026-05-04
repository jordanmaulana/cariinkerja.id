#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> git pull"
git pull --ff-only

echo "==> docker compose build"
docker compose --env-file .env.docker build

echo "==> docker compose up -d"
docker compose --env-file .env.docker up -d

echo "==> waiting for postgres healthy"
until [ "$(docker compose --env-file .env.docker ps -q postgres | xargs -I{} docker inspect -f '{{.State.Health.Status}}' {})" = "healthy" ]; do
  sleep 2
done

echo "==> django migrate"
docker compose --env-file .env.docker exec -T backend uv run manage.py migrate --noinput

echo "==> done"
docker compose --env-file .env.docker ps
