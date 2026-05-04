#!/bin/sh
set -e

if [ -n "${POSTGRES_HOST:-}" ]; then
  until uv run python -c "import socket,os; s=socket.socket(); s.settimeout(1); s.connect((os.environ['POSTGRES_HOST'], int(os.environ.get('POSTGRES_PORT','5432'))))" 2>/dev/null; do
    echo "waiting for postgres at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
    sleep 1
  done
fi

if [ "${ROLE:-web}" = "web" ]; then
  uv run manage.py migrate --noinput
  uv run manage.py collectstatic --noinput
fi

exec "$@"
