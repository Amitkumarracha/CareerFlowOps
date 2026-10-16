PYTHON := .venv/bin/python
UV := .venv-tools/bin/uv
DOCKER ?= docker
.PHONY: setup ml-setup dev test lint format db-migrate ingest train evaluate reproduce monitoring
setup:
	python infra/scripts/configure.py
	python -m venv .venv-tools
	.venv-tools/bin/pip install uv
	$(UV) venv --python 3.12 .venv
	$(UV) pip sync --python .venv/bin/python requirements-dev.lock
	cd apps/web && npm ci

ml-setup:
	$(UV) pip sync --python .venv/bin/python --extra-index-url https://download.pytorch.org/whl/cpu requirements-ml.lock

monitoring:
	$(DOCKER) compose --profile monitoring up -d

reproduce:
	$(PYTHON) infra/scripts/host.py .venv/bin/dvc repro
	.venv/bin/dvc push

dev:
	python infra/scripts/configure.py
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
	$(PYTHON) infra/scripts/host.py .venv/bin/alembic -c apps/api/alembic.ini upgrade head

ingest:
	$(PYTHON) infra/scripts/host.py $(PYTHON) -m pipelines.ingest

train:
	$(PYTHON) infra/scripts/host.py $(PYTHON) -m pipelines.train

evaluate:
	$(PYTHON) infra/scripts/host.py $(PYTHON) -m pipelines.evaluate
