# Implementation status

Implementation in progress. Original feature documentation was absent; see 32_DECISIONS.md.

Checks and limitations will be recorded with actual execution evidence.

## Phase 1 — bootstrap

Added API config/db/health/readiness, migrations scaffold, strict React/Vite/Tailwind frontend, Dockerfiles/Compose, dependency locks, Makefile and setup docs. PostgreSQL 16 started healthy on the system Docker daemon. Alembic upgrade completed. Live API /health and /ready and frontend / returned HTTP 200. Initial Python test passed; Python lint/format passed. Frontend checks recorded after dependency audit fixes. Full image builds will be verified after feature implementation. No GitHub remote supplied; local Git initialized for requested phase commits.

## Phase 2 — canonical database

Added SQLAlchemy entities for jobs/company/sources/provenance, candidates/profiles/resumes/skills, saved jobs/applications/history, experiments/deployments and ingestion runs. Generated explicit Alembic migration and applied it to PostgreSQL. Tests cover multi-source provenance and uniqueness.

## Phase 3 — ingestion

Added shared validated DTO/interface, official GET adapters for Greenhouse/Lever/Ashby, allowlisted boards, bounded HTTP retries, content-addressed raw archives, transactional idempotent ingestion, protected admin run/status endpoints and CLI. Captured 10 real postings per source with manifest. Eight backend tests passed including adapter fixtures, idempotency and partial failure. PostgreSQL fixture CLI succeeded twice (30 source occurrences, 29 canonical jobs). Python lint/format passed. Optional Workday/JobSpy remain disabled as scoped.

## Phase 4 — deduplication

Deterministic normalized company/title/location fingerprints share canonical jobs without deleting occurrences. Added bounded admin diagnostics with conservative fuzzy-title suggestions (never automatic merges). Ten backend tests passed, including cross-source/case/whitespace dedup, location separation and protected admin provenance output. Lint/format passed.

## Phase 5 — React portal and search

Added paginated/filterable jobs API with validated query limits and provenance response contracts. Added all requested React routes, responsive dashboard/navigation, search/filter/detail screens and typed forms for candidate and operations workflows. Candidate/operations API wiring is completed in subsequent phases. Eleven backend tests passed; frontend typecheck/lint/tests/build passed before adding interaction tests, whose results are recorded in final verification. No browser screenshot or visual automation has been run.

## Phase 6 — resume and profile

Added protected PDF upload/retrieval/deletion, size/magic/encryption/page/text limits, PyMuPDF extraction, conservative evidence-backed fields and named sections, normalized skills, editable profile contracts and candidate-data deletion. Raw extracted text stays separate from structured profile. Fourteen backend tests passed; lint/format passed.

## Phase 7 — ranking experiments

Implemented TF-IDF, real all-MiniLM-L6-v2 SentenceTransformer and configurable hybrid ranking with all explanation fields, conservative experience checks and explicit fallback identity. Downloaded model and verified 384-dimensional embeddings. Built frozen 29-job dataset with six fictional candidate queries and explicitly agent-authored illustrative judgments; validation/test queries are disjoint. Eighteen backend tests passed. Actually ran training/indexing and held-out evaluation for all three algorithms; three MLflow runs contain computed metrics and dataset/git/seed metadata. Validation selected TF-IDF on this tiny benchmark; no claim of general model quality is made.

## Phase 8 — DVC

Initialized DVC with local ignored storage remote and six dependency-tracked stages. Actually ran dvc repro through ingestion, normalization, dataset construction, indexing, evaluation and registration; pushed cached outputs to the local DVC remote. Small source snapshots and labels remain in Git so a fresh checkout can reproduce without an inaccessible external data bucket. Private resumes are excluded.

## Phase 9 — MLflow registry

Added packaged PyFunc ranking model with fitted TF-IDF artifact, transformer weights, scoring configuration and shipped source modules. Registration creates actual ModelExperiment/ModelDeployment rows, assigns production alias and verifies loading/predicting through that alias. Real MLflow server logged experiments and registered versions 1 and 2 during manual and DVC validation. Runtime/ML dependency locks include CPU PyTorch. Docker MLflow service verification follows in final integration.
