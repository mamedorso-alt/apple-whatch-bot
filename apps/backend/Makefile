.PHONY: up down logs migrate test test-docker lint

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api

migrate:
	docker compose exec api alembic upgrade head

test:
	pytest -q

test-docker:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test_runner

lint:
	python -m compileall app tests
