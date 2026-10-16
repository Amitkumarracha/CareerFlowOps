# CareerFlowOps

**Discover earlier. Match smarter. Apply better.**

Official job discovery, explainable resume-aware matching, manual application tracking and aggregate TPO analytics. React/Vite/strict TypeScript/Tailwind + FastAPI/Pydantic/SQLAlchemy + PostgreSQL/Alembic, with DVC, MLflow, Prometheus and Grafana.

## Run locally

Prerequisites: Python 3.12 (setup can download it through uv), Node 22.18+ and Docker Compose. Allow at least 10 GB free disk for development environments, CPU ML dependencies and initial image build caches.

```sh
make setup
make dev
```

Setup creates an ignored, permission-restricted `.env` with generated database, candidate, admin and Grafana credentials. Existing `.env` files are preserved: replace `CHANGE_ME` consistently in `POSTGRES_PASSWORD`/`DATABASE_URL`, and fill distinct `CANDIDATE_API_TOKEN`, `ADMIN_API_TOKEN`, and `GRAFANA_ADMIN_PASSWORD` values if yours are still blank. Optional Hugging Face/AWS credentials can stay blank. Never put secrets in `VITE_` variables.

If Docker Desktop is unavailable but the system daemon runs:

```sh
DOCKER_HOST=unix:///var/run/docker.sock make dev
```

- Portal: http://localhost:5173
- API documentation: http://localhost:8000/docs
- Health/readiness: http://localhost:8000/health and http://localhost:8000/ready
- MLflow: http://localhost:5000

In the portal, open **Workspace access** and enter the candidate/admin tokens from your local `.env`. Candidate operations need the candidate token; TPO, MLOps and source administration need the admin token. Tokens stay in the current browser tab's session. Public job browsing needs no token.

This MVP deliberately has one server-owned candidate identity. It needs per-user identity and role management before multi-user deployment. Service ports bind to loopback; use the documented TLS edge only after deployment authorization.

## Discover, match and track

From **Source health**, refresh the configured public Greenhouse (Stripe), Lever (Palantir), and Ashby (Linear) boards. Or load **historical snapshots** for an offline demonstration; these are captured real postings with URLs/timestamps in `data/samples/manifest.json`. Fixtures cannot overwrite an already verified live occurrence.

```sh
make ingest
# Explicit offline mode:
.venv/bin/python infra/scripts/host.py .venv/bin/python -m pipelines.ingest --fixtures
```

Search by keyword, location, company, source, work arrangement, employment type, experience and posting date. Source occurrences and raw payload hashes remain separate from canonical jobs. Exact normalized fingerprints merge duplicates; fuzzy matches are diagnostic suggestions only. Missing source fields stay unknown.

Upload a selectable-text PDF (at most 5 MB / 30 pages), review the extracted profile and open **For you**. Recommendations explain component scores, matching/missing skills, experience checks and uncertainty. Ranking choices are the registered production model, TF-IDF, SentenceTransformer and hybrid. A fallback is always identified in the response/UI. Scores are content comparisons, not probabilities of being hired.

Save a job to add it to **Saved jobs** and start tracking it. Bookmarks persist across pages; removing one keeps application history. **Apply** opens the official employer URL; it never submits an application or claims submission. Update `SAVED`, `APPLIED`, `INTERVIEW`, `OFFER`, `REJECTED` or `WITHDRAWN` manually; notes and timestamp history persist. Delete stored candidate data from the profile page.

## Reproduce the ML workflow

With PostgreSQL and MLflow running:

```sh
make ml-setup
make reproduce
```

DVC runs `ingest -> preprocess -> build_training_set -> train -> evaluate -> register -> export_model`, then pushes versioned outputs to ignored local `dvc-storage`. Small real source snapshots and illustrative labels remain in Git so a fresh checkout can reproduce. The first run downloads the pinned public all-MiniLM-L6-v2 revision; subsequent runs can use cached weights. `params.yaml` controls weights, seed and embedding revision. Updating a model deliberately means updating its revision there.

Training creates a TF-IDF retrieval index and uses a pretrained SentenceTransformer, without supervised fine-tuning. Three MLflow experiments record actual metrics, latency, dataset hash, Git commit and seed. Validation selects the algorithm; test queries stay held out. Registration packages scoring code, fitted vocabulary, transformer weights and pinned dependencies, promotes `careerflowops-ranker@production`, and verifies prediction. Restart the API after promotion to reload its cached alias. The final export stage creates a checksummed production bundle for DVC delivery. Setting `MODEL_BUNDLE_PATH` makes the API require that bundle, verify its inference compatibility and pass a prediction probe before readiness; this mode never falls back to a different model. The AWS production Compose overlay configures this mode.

The demonstration benchmark has **29 frozen real jobs and six fictional candidate queries**. Relevance judgments were authored by the implementation agent and are **not human-validated**. These tiny illustrative measurements do not establish general model quality. The MLOps dashboard shows saved evaluation artifacts only; it shows no numbers until evaluation runs. Its frozen corpus is independent of live job ingestion.

`make train` and `make evaluate` run individual stages after their dataset prerequisites exist. If you switch to an empty MLflow server, use `dvc repro --force` through the host helper to recreate runs before registration. The local DVC remote is not shared cloud storage; configure authorized durable storage for collaboration. Never version resumes in DVC or MLflow.

## Development and checks

```sh
make test
make lint
make format
make db-migrate
make monitoring
```

Prometheus: http://localhost:9090; Grafana: http://localhost:3000 (`admin`, password from `.env`). Grafana's application/model dashboard and Prometheus data source are provisioned automatically. Ingestion counters cover runs executed inside the API process; a separate CLI process has its own metrics. API metrics are at http://localhost:8000/metrics.

For host development, use the helper to translate Compose service DNS to localhost without printing credentials:

```sh
.venv/bin/python infra/scripts/host.py .venv/bin/uvicorn apps.api.app.main:app --reload
# In another terminal, with the Compose frontend stopped:
cd apps/web && npm run dev
```

Python tests use isolated SQLite databases and fixture HTTP responses; CI also runs PostgreSQL migrations. Frontend tests cover search/error states, official Apply URLs, access errors and authenticated Save. See [verification evidence](docs/IMPLEMENTATION_STATUS.md) for checks actually run. GitHub workflow execution and AWS deployment require a real remote/account and are not implied by local checks.

See the [completed UI and demonstration guide](docs/UI_FEATURE_GUIDE.md) for all pages, workflows and commands. **System & guide** shows the model/deployment lifecycle and live readiness. Resume history supports reviewing and deleting stored extractions; Applications supports status/search filters; Model experiments supports split filtering and downloading saved evaluation JSON.

## Deployment and limits

[EC2/ECR instructions and permission templates](infra/aws/README.md) prepare GitHub OIDC, SHA-tagged images, private Compose services, optional Caddy TLS and deployment health checks. No cloud provisioning or publishing is automatic without configured access and authorization.

MVP limits: one candidate identity; known-skill dictionary and heuristic resume sections; no OCR; no automatic closed-job detection; recommendations inspect the most recent 1,000 active records; TPO match/gap/category breakdown inspects 100 jobs / 500 profiles and shows that scope. Unknown eligibility is neutral and explicitly explained. Workday/JobSpy are disabled until company-specific integration policies are reviewed. User-submitted social links and advanced authentication are outside this implementation.

Original numbered design files were absent. They were reconstructed from the supplied brief, with this gap recorded in [decisions](docs/32_DECISIONS.md); original instructions and the brief are preserved. See [START_HERE.md](START_HERE.md) and [source references](docs/REFERENCES.md).
