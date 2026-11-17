.PHONY: help up down build logs test lint format audit migrate seed backup restore contrast

PYTHON ?= .venv312/bin/python
PYTEST ?= .venv312/bin/pytest
RUFF ?= .venv312/bin/ruff
FLASK ?= .venv312/bin/flask
PIP_AUDIT ?= .venv312/bin/pip-audit

help:
	@echo "Hedgewar Hospital Care — Management Commands"
	@echo "============================================="
	@echo "  make up        : Start application and dependencies in Docker"
	@echo "  make down      : Stop all Docker containers"
	@echo "  make build     : Build Docker images"
	@echo "  make logs      : Stream Docker container logs"
	@echo "  make test      : Run complete pytest test suite with coverage"
	@echo "  make lint      : Run ruff linter and format verification"
	@echo "  make format    : Auto-format code using ruff"
	@echo "  make audit     : Run pip-audit for dependency security"
	@echo "  make contrast  : Verify WCAG 2.2 AA accessibility contrast ratios"
	@echo "  make migrate   : Apply database schema migrations"
	@echo "  make seed      : Seed database with realistic 6-month demo dataset"
	@echo "  make backup    : Execute transactional database backup"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

test:
	$(PYTEST) --cov=hms tests/

lint:
	$(RUFF) check hms/ tests/
	$(RUFF) format --check hms/ tests/

format:
	$(RUFF) format hms/ tests/
	$(RUFF) check --fix hms/ tests/

audit:
	$(PIP_AUDIT)

contrast:
	$(PYTHON) tools/check_contrast.py

migrate:
	$(FLASK) db upgrade

seed:
	$(FLASK) seed-demo

backup:
	bash scripts/backup.sh
