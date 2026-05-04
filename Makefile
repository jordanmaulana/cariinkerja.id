ARCH := $(shell uname -m)

upgrade:
	uv sync
	uv lock --upgrade
	uv sync --frozen --no-install-project

audit:
	cd frontend && pnpm audit fix

lint:
	uv run ruff format .
	uv run ruff check . --fix

dev:
	uv run manage.py runserver 8000

mmg:
	uv run manage.py makemigrations

migrate:
	uv run manage.py migrate

tw-run:
	npx @tailwindcss/cli -i ./static/input.css -o ./static/output.css --watch

tw-build:
	npx @tailwindcss/cli -i ./static/input.css -o ./static/output.css

web:
	cd frontend && pnpm run dev

worker:
	OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES uv run celery -A core worker -l info

beat:
	uv run celery -A core beat -l info

dock:
	docker compose --env-file .env.docker down
	docker compose --env-file .env.docker build
	docker compose --env-file .env.docker up -d
	docker compose --env-file .env.docker logs -f