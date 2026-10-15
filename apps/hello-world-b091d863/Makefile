# Detect container engine
ENGINE := $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)
ifeq ($(ENGINE),podman)
  COMPOSE := podman-compose
else
  COMPOSE := docker compose
endif

.PHONY: up down logs build test backend-test frontend-test audit

up:
	$(COMPOSE) up --build -d
	@echo "App: http://localhost:8080"

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f --tail=200

build:
	$(COMPOSE) build

test: backend-test frontend-test

backend-test:
	cd backend && python -m pytest

frontend-test:
	cd frontend && npm test

audit:
	cd backend && pip-audit -r requirements.txt || true
	cd frontend && npm audit --omit=dev || true
