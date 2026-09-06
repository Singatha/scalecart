SHELL := /bin/sh
COMPOSE := docker compose
PYTHON ?= python3.12
VENV := .venv

.PHONY: up down logs ps build test test-backend test-frontend lint lint-backend lint-frontend format migrate seed install-backend install-frontend

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

install-backend:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -e 'packages/python-common[test]' ruff
	@for service in services/*-service; do $(VENV)/bin/pip install -e "$$service[test]"; done

install-frontend:
	npm ci --prefix apps/storefront

test: test-backend test-frontend

test-backend:
	$(VENV)/bin/pytest packages/python-common/tests
	@for service in services/*-service; do (cd "$$service" && PYTHONPATH=. ../../$(VENV)/bin/pytest tests) || exit 1; done

test-frontend:
	npm test --prefix apps/storefront

lint: lint-backend lint-frontend

lint-backend:
	$(VENV)/bin/ruff check packages services
	$(VENV)/bin/ruff format --check packages services

lint-frontend:
	npm run lint --prefix apps/storefront

format:
	$(VENV)/bin/ruff check --fix packages services
	$(VENV)/bin/ruff format packages services

migrate:
	$(COMPOSE) exec user-service alembic upgrade head
	$(COMPOSE) exec product-service alembic upgrade head
	$(COMPOSE) exec order-service alembic upgrade head
	$(COMPOSE) exec payment-service alembic upgrade head

seed:
	$(COMPOSE) exec user-service python -m app.seed
	$(COMPOSE) exec product-service python -m app.seed
