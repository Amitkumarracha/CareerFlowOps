# CareerFlowOps — Start Here

## Project in one sentence
CareerFlowOps is an end-to-end MLOps platform that continuously collects job openings from public/official sources, normalizes and deduplicates them, ranks them against a candidate's resume/profile, explains the match, and helps students track and act on opportunities through a React web application.

## Academic title
**CareerFlowOps: An End-to-End MLOps Platform for Real-Time Job Discovery, Resume-Aware Ranking and Application Intelligence**

## Product tagline
**Discover earlier. Match smarter. Apply better.**

## Why this is an MLOps project
The project is not only a job portal. The ML ranking system is versioned, evaluated, registered, deployed, monitored, and improved through an MLOps lifecycle:

`Raw Jobs + Candidate Data -> DVC -> Preprocessing -> Experiments -> MLflow -> Best Model -> Model Registry -> FastAPI -> Docker -> GitHub Actions -> AWS ECR/EC2 -> Monitoring -> Feedback -> Retraining`

## MVP users
1. **Student / job seeker** — uploads resume, gets ranked jobs, checks eligibility/skills gaps, saves/applies, tracks outcomes.
2. **TPO / placement team** — sees opportunities, eligible-student counts, applications and placement analytics.
3. **Admin** — manages data sources, ingestion health, duplicate jobs, model version and system health.

## MVP sources
Prioritize official/public career sources first:
- Greenhouse job boards
- Lever postings
- Ashby public job postings
- Selected company career pages / Workday adapters
- Optional JobSpy connector for development/experimentation where usage is permitted
- User-submitted job links/text as leads, then verify against an official source

## MVP principles
- Never fabricate job data or ML metrics.
- Prefer official career pages over social reposts.
- Deduplicate the same opening across multiple sources.
- Do not blindly auto-apply to thousands of jobs.
- MVP action is **Review & Apply** using the official employer link.
- Keep a human in the loop for application submission.
- Treat social posts/reels as leads, not authoritative jobs.
- Record source, first_seen, last_seen, posted_at, verified_at and application URL.

## Recommended 3-day build scope
### Day 1 — Data + portal
- Ingestion adapters
- Normalized job schema
- Deduplication
- PostgreSQL
- React search/browse UI

### Day 2 — Intelligence
- Resume upload/parser
- Candidate profile extraction
- TF-IDF baseline
- SentenceTransformer semantic matcher
- Hybrid ranking
- Missing-skill / eligibility explanation
- Application tracker

### Day 3 — MLOps
- DVC data pipeline
- MLflow experiment tracking and registry
- FastAPI inference endpoints
- Docker
- GitHub Actions
- AWS ECR/EC2 deployment path
- Monitoring dashboard
- TPO analytics

## Environment configuration

Copy the shared template before configuring local services:

```sh
cp .env.example .env
```

Replace `CHANGE_ME` in both `POSTGRES_PASSWORD` and `DATABASE_URL` with the same local password. URL-encode special characters in the URL password. Keep credentials in `.env`, which is ignored by Git; leave optional tokens and AWS credentials blank until needed. Variables prefixed with `VITE_` are exposed to the browser and must never contain secrets.

The template uses Docker network service names `postgres` and `mlflow`. When running the API directly on your machine, use `localhost` and the services' published ports instead. `VITE_API_BASE_URL` is a browser-facing address; update it and `CORS_ORIGINS` for your actual frontend/API origins.

See `README.md` for executable setup commands and `docs/IMPLEMENTATION_STATUS.md` for current verification evidence. Numbered feature documents were reconstructed from the supplied brief because the originals were absent; see `docs/32_DECISIONS.md`.

For the complete remaining stages, current progress, Git/DVC commands, AWS deployment, assessment evidence and future feature priorities, follow [docs/remaining/README.md](docs/remaining/README.md).

## Read next
1. `docs/01_PROJECT_CHARTER.md`
2. `docs/02_PRODUCT_REQUIREMENTS.md`
3. `docs/03_SYSTEM_ARCHITECTURE.md`
4. `docs/04_REPO_STRUCTURE.md`
5. `AGENTS.md` before asking Codex to implement.
