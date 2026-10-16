# CareerFlowOps

Discover earlier. Match smarter. Apply better.

A React + FastAPI + PostgreSQL platform for official job discovery, explainable resume-aware matching, manual application tracking and aggregate TPO analytics.

## Local setup

Use Python 3.12, Node 22 and Docker Compose. Copy `.env.example` to `.env`, replace the database password in both fields, and generate distinct `CANDIDATE_API_TOKEN` and `ADMIN_API_TOKEN` values (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). Never commit `.env`.

```sh
make setup
make dev
```

Open http://localhost:5173 and API docs at http://localhost:8000/docs. For a host API process, change DATABASE_URL host to localhost. Run `make db-migrate` then `.venv/bin/uvicorn apps.api.app.main:app --reload` and `cd apps/web && npm run dev`.

If Docker Desktop is unavailable but the system daemon runs, use `DOCKER_HOST=unix:///var/run/docker.sock make dev`.

`make test`, `make lint`, `make format`, `make ingest`, `make train`, and `make evaluate` provide development commands. Read [decisions](docs/32_DECISIONS.md) and [implementation status](docs/IMPLEMENTATION_STATUS.md) for scope and actual verification evidence.
