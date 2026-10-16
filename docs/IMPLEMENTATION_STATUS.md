# Implementation status

Local MVP implemented and verified on 16 October 2026. GitHub publishing and AWS deployment await external repository/account access and cloud authorization. Original feature documentation was absent; see 32_DECISIONS.md.

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

## Phase 10 — recommendations

Added protected /api/jobs/recommended before dynamic job routing, profile-required validation, score filtering and bounded results, all explanation fields and production-registry inference with explicit local fallback. UI can select production or any experiment algorithm. Twenty backend tests passed including recommendation validation and registry failure. Local ranking examines at most the 1000 most recently seen active jobs; retrieval scaling is a documented MVP limit.

## Phase 11 — application tracker

Added protected idempotent save/unsave and application creation/list/update, all six statuses, owner checks and append-only timestamp/notes history. Repeating unchanged updates does not create history. Corrected concurrent candidate creation and restricted PostgreSQL row locks to applications. Twenty-two backend tests passed at this phase, including repeated save/status requests and cross-candidate privacy.

## Phase 12 — TPO analytics

Added protected aggregate TPO endpoint with real student/job/application counts, company/category/skill-gap distributions, current-status funnel and potential candidate matching counts. No names, emails or resume text are returned. Match breakdown is explicitly bounded to 100 jobs/500 active profiles. Added saved-artifact MLOps dashboard API. Aggregate privacy and zero-data tests passed.

## Phase 13 — monitoring

Added /metrics, bounded route-label HTTP counters/latencies, ingestion/source/failure/normalization/dedup counters, recommendation/inference/score metrics and model identity. Structured route/status/duration logs omit request bodies and credentials. Added multipart upload stream/length limits, safe DB error responses, Prometheus scrape configuration and provisioned Grafana dashboards. Twenty-five backend tests passed including metrics labels, disabled metrics, aggregate privacy and upload guard. Monitoring containers are optional via the monitoring Compose profile and will be checked in final integration.

## Phase 14 — CI/CD

Added reusable PR/manual CI for backend format/lint/tests/PostgreSQL migrations and frontend type/lint/format/tests/build/audit. Main runs complete CI before SHA-tagged API/web Docker builds; ECR push requires configured OIDC role and otherwise skips. Both local Docker images built successfully; frontend production build/type/lint and five tests passed; backend reached 27 passing tests. No GitHub remote was supplied, so hosted Actions success is not claimed.

## Phase 15 — AWS preparation

Added EC2 deployment script with explicit immutable ECR image requirements, instance-role login, Compose migration/startup and readiness verification; prepared OIDC trust/ECR permission templates and optional Caddy TLS edge configuration. Documented operator steps, private service bindings, backups and single-candidate limitations. bash syntax check and missing-image guard test passed. No AWS credentials, repository remote, domain, cloud provisioning or deployment authorization was supplied; no cloud actions were performed.

## Phase 16 — final local verification

| Check actually run | Result |
| --- | --- |
| Backend suite in fresh requirements-dev.lock environment | 30 passed; one upstream Starlette/httpx deprecation warning |
| Python lint and formatting | Passed |
| Frontend strict TypeScript, ESLint, Prettier | Passed |
| Vitest / React Testing Library | 5 passed (search/filter/error, official Apply, authenticated Save, access errors, edited profile submission) |
| Frontend production build | Passed; Vite 8 |
| npm dependency audit | Zero reported vulnerabilities |
| PostgreSQL 16 + explicit Alembic migration | Started healthy; upgrade passed; final schema-drift check reported no new operations |
| API and web Docker builds | Passed; final ingestion fix layered onto the tested local API image after clearing intermediate caches |
| Running Compose services | PostgreSQL, API, frontend, MLflow, Prometheus and Grafana |
| Real public ATS ingestion | 1,069 fetched/normalized (729 Greenhouse + 309 Lever + 31 Ashby), 1,061 canonical jobs, all 1,069 source occurrences retained |
| Repeated live admin ingestion | Succeeded; zero added duplicates; ingestion counters/model identity exposed |
| Running API smoke workflow | PDF upload/profile extraction; all three rankers without fallback; registered production prediction; idempotent Save; five manual status changes with six history entries; protected TPO/MLOps/admin; metrics |
| Frontend HTTP serving | All ten requested routes returned HTTP 200 from the built Nginx frontend |
| Model download/inference | Real all-MiniLM-L6-v2, 384 dimensions; upstream revision pinned in params.yaml |
| Full DVC workflow | All six stages ran; outputs pushed to local remote; subsequent repro reused unchanged train/evaluate outputs |
| MLflow registry | Actual production version 3; loaded/predicted through alias; repeated registration reused version 3 |
| Monitoring | Prometheus target up=1; Grafana health OK; provisioned careerflowops dashboard with 11 panels |
| CI/deployment files | YAML/JSON parsed; shell syntax passed; missing-image guard tested |
| Secret check | Generated runtime credentials absent from tracked files; .env ignored |

Final review also verified that historical fixtures cannot overwrite verified live data, and source title/location edits keep canonical identity and application history. Fingerprint collisions with another existing job remain separate for manual review. Temporary smoke-test candidate/resume/application data was deleted; real job data and experiment artifacts remain.

### Verification limits and remaining external steps

- No GitHub repository URL/remote was provided. Local conventional commits exist; no push or hosted GitHub Actions run is claimed.
- AWS account/role, host, domain and deployment authorization were not provided. ECR/EC2/TLS files are prepared; no cloud resource creation, publishing or deployment was attempted.
- No interactive browser/visual/responsive screenshot QA was performed. React interaction tests, production builds, and HTTP serving were checked.
- This is a single-candidate authenticated MVP, with heuristic PDF sections and a known-skill dictionary, no OCR and no automatic closed-job detection. Add real multi-user identity before a shared production launch.
- Evaluation labels are implementation-agent-authored illustrative judgments for six fictional queries against 29 frozen real jobs, not human-validated or representative production evaluation. Metrics are measured, never fabricated.
- Recommendations inspect at most 1,000 recent jobs; TPO match/gap/category breakdown uses at most 100 jobs and 500 active profiles. Global headline counts come from persisted records. CLI counters live in a separate process; use admin ingestion for API-scraped ingestion counters.
- Only task-owned build intermediates/temporary model downloads were removed to recover disk space. Runnable images, databases, DVC artifacts and unrelated project caches were preserved. The machine remains low on free disk; reserve additional capacity before rebuilding large inference images.

## UI and model-delivery completion update

This update supersedes the earlier limitations about missing browser QA and model delivery. Origin is now the user-supplied `https://github.com/Amitkumarracha/CareerFlowOps.git`; publishing outcome is recorded below. AWS remains operator-configured, as requested.

- Added Saved jobs and System & guide pages, persistent bookmark save/unsave, URL-backed job filters, detail-page bookmarks, resume history/text review/deletion, application search/status filters, evaluation split filtering/JSON export, linked duplicate review, retry states and accessible mobile navigation.
- Workspace access updates/disconnect cancel requests, clear cached private data and remount the active view. Profile edits persist on reload; extracted resume deletion retains the edited profile.
- Added the seventh DVC `export_model` stage and a complete selected-model bundle with evaluation/registry/training metadata, file checksums and inference-code/runtime-lock compatibility checks. The actual TF-IDF production release was exported, pushed to the local remote, pulled into a fresh isolated DVC workspace and validated with inference.
- Added fail-closed bundle serving and readiness with actual prediction/model identity. The real release was exercised through an isolated API: `/ready` reported `b3e854956e87-fbb63052`; recommendations returned the same version, explanations and no fallback. The updated API image also validated this bundle successfully.
- EC2 deployment now pulls the model before startup, validates it inside the published API image, requires image tags matching the checkout SHA and verifies the running bundle ID. Fake-tool deployment tests verify that model validation failures prevent service startup. IAM rendering tests verify repository restrictions and EC2 read-only storage/image access.
- Added pinned DVC/S3 deployment dependencies, an IAM document renderer, production Compose overlay, `unless-stopped` service restart policies and a complete AWS setup/deployment runbook. No AWS API calls, paid resource creation or cloud deployment occurred.
- Browser validation used real Chromium, an isolated SQLite database, frozen real ATS fixtures and a fictional candidate. Access, profile persistence, bookmark persistence, search Back navigation, application update/filter, resume upload/review/delete, mobile navigation and disconnect passed. Twelve route variants plus the job-detail flow were exercised. All eleven main pages fit desktop, 390px and 320px widths without page-wide overflow; no JavaScript page errors occurred. Desktop overview/jobs/system and mobile jobs screenshots were visually inspected.
- Updated local API/web images were built using the existing runtime layers and started with PostgreSQL, MLflow, Prometheus and Grafana. Public browser smoke confirmed the updated `/`, `/jobs`, `/saved` and `/system` views at port 5173. API readiness, MLflow, Prometheus and Grafana health requests succeeded. The production runtime base was reused; a new clean dependency-image rebuild was not performed because free disk is low.
- Final test/check outcomes: 44 backend tests in the base dependency environment; 13 frontend tests; Python Ruff lint/format; strict TypeScript, ESLint, Prettier and Vite production build. All passed. The base Python environment reports one upstream Starlette/httpx deprecation warning.
- Only the identified API overlay build-cache chain created during this update was pruned, recovering about 2 GB. Running images, databases, DVC artifacts and other project caches were preserved; approximately 2.5 GB remained free.

See UI_FEATURE_GUIDE.md for pages, run commands and scope, and ../infra/aws/README.md for all AWS commands. Real multi-user identity, OCR, scheduled ingestion/closed-job expiry, a larger human-labeled benchmark and scaling remain future product work. The current model metrics remain small illustrative measurements, not production-quality evidence.
