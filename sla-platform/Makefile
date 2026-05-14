.PHONY: up down build logs migrate test

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

migrate-create:
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

test:
	docker compose exec backend pytest

shell:
	docker compose exec backend python

worker-logs:
	docker compose logs -f worker

restart:
	docker compose restart

clean:
	docker compose down -v
	docker system prune -f
