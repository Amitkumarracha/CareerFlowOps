# Implementation status

Implementation in progress. Original feature documentation was absent; see 32_DECISIONS.md.

Checks and limitations will be recorded with actual execution evidence.

## Phase 1 — bootstrap

Added API config/db/health/readiness, migrations scaffold, strict React/Vite/Tailwind frontend, Dockerfiles/Compose, dependency locks, Makefile and setup docs. PostgreSQL 16 started healthy on the system Docker daemon. Alembic upgrade completed. Live API /health and /ready and frontend / returned HTTP 200. Initial Python test passed; Python lint/format passed. Frontend checks recorded after dependency audit fixes. Full image builds will be verified after feature implementation. No GitHub remote supplied; local Git initialized for requested phase commits.

## Phase 2 — canonical database

Added SQLAlchemy entities for jobs/company/sources/provenance, candidates/profiles/resumes/skills, saved jobs/applications/history, experiments/deployments and ingestion runs. Generated explicit Alembic migration and applied it to PostgreSQL. Tests cover multi-source provenance and uniqueness.

## Phase 3 — ingestion

Added shared validated DTO/interface, official GET adapters for Greenhouse/Lever/Ashby, allowlisted boards, bounded HTTP retries, content-addressed raw archives, transactional idempotent ingestion, protected admin run/status endpoints and CLI. Captured 10 real postings per source with manifest. Eight backend tests passed including adapter fixtures, idempotency and partial failure. PostgreSQL fixture CLI succeeded twice (30 source occurrences, 29 canonical jobs). Python lint/format passed. Optional Workday/JobSpy remain disabled as scoped.
