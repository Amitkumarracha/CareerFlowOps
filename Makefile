PYTHON := .venv/bin/python
UV := .venv-tools/bin/uv
DOCKER ?= docker
.PHONY: setup dev test lint format db-migrate ingest train evaluate
setup:
	python -m venv .venv-tools
	.venv-tools/bin/pip install uv
	$(UV) venv --python 3.12 .venv
	$(UV) pip sync --python .venv/bin/python requirements-dev.lock
	cd apps/web && npm ci

dev:
	$(DOCKER) compose up --build -d

test:
	$(PYTHON) -m pytest
	cd apps/web && npm test

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	cd apps/web && npm run typecheck && npm run lint && npm run format:check

format:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .
	cd apps/web && npm run format

db-migrate:
	.venv/bin/alembic -c apps/api/alembic.ini upgrade head

ingest:
	$(PYTHON) -m pipelines.ingest

train:
	$(PYTHON) -m pipelines.train

evaluate:
	$(PYTHON) -m pipelines.evaluate
