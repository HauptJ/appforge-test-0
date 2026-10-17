# Hello World 0 - developer convenience targets.
# Detects podman/docker automatically.

SHELL := /bin/sh

ENGINE  := $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)
ifeq ($(ENGINE),podman)
COMPOSE := podman-compose
else
COMPOSE := docker compose
endif

.PHONY: up down logs build test

up:
	$(COMPOSE) up --build -d
	@echo "Service URL: http://127.0.0.1:8080/api/v1/hello"

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

build:
	$(COMPOSE) build

test:
	cd backend && python -m pytest
