#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> git pull"
git pull --ff-only

echo "==> docker compose build"
docker compose build

echo "==> docker compose up -d"
docker compose up -d

echo "==> waiting for postgres healthy"
until [ "$(docker compose ps -q postgres | xargs -I{} docker inspect -f '{{.State.Health.Status}}' {})" = "healthy" ]; do
  sleep 2
done

echo "==> django migrate"
docker compose exec -T backend uv run manage.py migrate --noinput

echo "==> django collectstatic"
docker compose exec -T backend uv run manage.py collectstatic --noinput

echo "==> restart backend / worker / beat / frontend"
docker compose restart backend worker beat frontend

echo "==> done"
docker compose ps
