# AGENTS.md — Instructions for Codex / Coding Agents

## Mission
Build **CareerFlowOps**, a production-oriented MLOps project for job discovery, resume-aware ranking, application tracking and TPO analytics.

## Read order before coding
1. `START_HERE.md`
2. `docs/02_PRODUCT_REQUIREMENTS.md`
3. `docs/03_SYSTEM_ARCHITECTURE.md`
4. `docs/04_REPO_STRUCTURE.md`
5. The feature-specific document for the task.

## Core stack
- Frontend: React + Vite + TypeScript
- Backend: FastAPI + Pydantic
- Database: PostgreSQL
- ORM: SQLAlchemy 2.x or SQLModel
- ML: scikit-learn + sentence-transformers
- MLOps: DVC + MLflow
- Containers: Docker + Docker Compose
- CI/CD: GitHub Actions
- Cloud target: AWS ECR + EC2
- Monitoring: Prometheus + Grafana; Evidently optional for ML drift

## Mandatory coding rules
- TypeScript strict mode.
- Python type hints for public functions.
- Pydantic schemas for API request/response contracts.
- Never hard-code secrets, tokens or passwords.
- All external integrations live behind adapters/interfaces.
- Store raw source payloads separately from normalized jobs.
- Upserts must be idempotent.
- Every job must preserve `source_name`, `source_job_id`, `source_url`, and `apply_url`.
- Duplicate detection must never delete source provenance.
- Model output must include explanation fields, not only a score.
- ML metrics shown in UI must come from saved experiment/evaluation artifacts.
- Do not invent evaluation numbers in seed data or screenshots.

## Source/compliance rules
- Prefer official/public ATS endpoints and career pages.
- Respect source terms, rate limits and robots/policies where applicable.
- Do not implement credential bypass, anti-bot circumvention, CAPTCHA bypass or bulk unauthorized auto-submission.
- Social-media URLs are user-submitted leads in MVP; verify them against official employer sources when possible.
- Application MVP = direct official apply link + user review.

## Definition of done for any feature
- Implementation complete.
- Unit tests added/updated.
- API validation and error states handled.
- Relevant docs updated.
- No secrets committed.
- Docker/dev environment still starts.
- Lint/type-check/tests pass.

## Avoid scope creep
Do not introduce Kafka, Kubernetes, microservices, LLM agents or browser automation unless a specific milestone explicitly requests them. The MVP should remain buildable in 2–3 days.
