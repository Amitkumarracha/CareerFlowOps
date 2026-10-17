# Overall progress, requirements and known gaps

Reviewed: **17 October 2026**. This is an evidence-based status report, not a completion percentage. The historical implementation log remains in [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).

## Current result

The local application and MLOps release path are implemented and tested. GitHub authentication, hosted workflow success and AWS deployment have not been demonstrated. The latest recorded push failed because HTTPS authentication was missing. Read-only origin inspection during this review returned no refs.

Current runtime checks during this review:

| Check | Observed result |
| --- | --- |
| API health and readiness | HTTP 200 at port 8000 |
| Local jobs endpoint | 1,061 canonical jobs at review time; this count changes with ingestion |
| Docker services | API, web, PostgreSQL, MLflow, Prometheus and Grafana running |
| Current readiness mode | Development: model fields are null; this is not an EC2/bundle-mode verification |
| Selected model artifact | TF-IDF, `b3e854956e87-fbb63052` |
| Saved MLflow registry metadata | `careerflowops-ranker@production`, version 3 |
| Exported DVC production bundle | Present locally |
| Git implementation commits | `9596657` and follow-up documentation commit `12e8473`; subsequent documentation commits may follow |
| Workstation prerequisites missing | `aws` and `gh` were not on PATH during review |
| Available disk | About 2.1 GB at review time; insufficient headroom for a clean full ML image rebuild |

Do not delete project databases, volumes, artifacts or unrelated caches to free space. Choose storage deliberately before large builds. Image publishing can run on a GitHub-hosted runner once access is configured.

## Completed functionality

| Area | Implemented | Remaining boundary |
| --- | --- | --- |
| React portal | Overview, search, job details, recommendations, saved jobs, profile, resume, applications, TPO, experiments, source health, system guide, not-found view | Continue accessibility and real-user usability review |
| Search | Keyword, location, company, source, work arrangement, employment, experience and posting-date filters; URL state and pagination | Recommendation retrieval still examines at most 1,000 recent active jobs |
| ATS ingestion | Greenhouse, Lever and Ashby adapters, bounded retries, allowlisted boards and live/snapshot modes | Scheduled ingestion, expiry/revalidation and more employer boards |
| Data quality | Raw payloads separate from normalized jobs, idempotent upserts, source occurrences and preserved apply URLs | Fuzzy matches are suggestions; no merge/reject review workflow |
| Resume/profile | Text PDF extraction, known-skill normalization, editable profile, history/text review and owner-checked deletion | No OCR or broad entity-recognition model |
| Ranking | TF-IDF, pretrained SentenceTransformer and hybrid; component scores and explanations | Human-validated larger benchmark; no claim of hiring probability |
| Applications | Persistent bookmarks, official Apply, six manual states, notes/history, search/status filters | No reminders, calendar integration or automatic submission |
| TPO | Actual aggregate counts, distributions, potential matches and disclosed sample limits | A real cohort model and per-user roles are absent |
| MLflow | Actual experiment runs, metrics/artifacts, model versions and production alias | Local backend/artifacts are not automatically replicated to a new EC2 host |
| DVC | Seven stages and a self-contained selected-model bundle, local push and fresh isolated pull verified | Production S3 remote must be configured and populated |
| Production serving | File/inference compatibility validation, prediction probe, fail-closed bundle inference, readiness identity | Must execute the EC2 deployment and verify the downloaded release there |
| Containers | API/web images, Compose, migrations, persistence and restart policies | Latest local update reused installed runtime layers due disk limits |
| CI/CD | GitHub checks, SHA-tagged builds and optional OIDC ECR publishing | Hosted execution unverified; EC2 promotion is operator-driven |
| Monitoring | Prometheus metrics, structured HTTP logs and provisioned Grafana dashboard | No alert notifications, automated SLO enforcement or ML drift pipeline |
| Access/privacy | Separate candidate/admin bearer tokens, private candidate endpoints and cache clearing on disconnect | Candidate token identifies one candidate; not a multi-user platform |

## Verification already performed

The previous implementation turn actually ran:

- 44 backend tests in the base dependency environment; one upstream Starlette/httpx deprecation warning.
- 13 frontend tests, strict TypeScript, ESLint, Prettier, Ruff and a Vite production build.
- Chromium candidate flows using a temporary SQLite database: access, profile save/reload, saved-job persistence, search Back navigation, application changes/filtering, resume upload/review/delete, mobile navigation and disconnect.
- Twelve main route variants, a job-detail flow, mobile widths of 390px and 320px, with no page-wide overflow or JavaScript page errors observed.
- Actual model export, local DVC push, fresh isolated DVC pull, bundle inference, API readiness/prediction and validation inside the API image.
- Fake-tool deployment tests: invalid models prevent service startup. These test the deployment control flow; they do not substitute for real AWS execution.

This documentation update rechecked local runtime and saved artifact identity. It did not rerun the entire test suite or provision AWS. Use [the commands guide](02_GIT_DVC_RELEASE.md) for repeatable checks.

## Model quality: what the evidence means

The frozen benchmark has **29 real ATS jobs and six fictional candidate queries**. Relevance labels were authored by the implementation agent, are illustrative and are not human validated. There are two training, two validation and two held-out test queries. The transformer is pretrained; it was not supervised-fine-tuned on resumes.

Validation quality metrics tied across the three approaches, and the documented deterministic tie-break selected TF-IDF. The saved metrics prove that evaluation ran; they do not establish general superiority, fair hiring decisions or representative production accuracy. The MLOps UI reads saved evaluation artifacts rather than invented numbers.

The training commit in `training.json` predates the UI changes. This is intentional provenance. A deployment can reuse the model when its inference code/runtime lock remain compatible; new data or scoring changes require reproduction and evaluation.

## Stack and external requirements

| Layer | Current technology | Account/key needed? |
| --- | --- | --- |
| Frontend | React, Vite, strict TypeScript, TanStack Query, Router, Tailwind, Lucide | No external paid API |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic | Generated local candidate/admin tokens |
| Database | PostgreSQL 16 | Protected database password in `.env` |
| ML | scikit-learn, CPU SentenceTransformer/PyTorch | Public model download; optional HF token only if upstream access requires it |
| Data sources | Public Greenhouse, Lever, Ashby endpoints | Current adapters do not require paid aggregator keys |
| Versioning | Git/GitHub and DVC | GitHub write access; S3 access for shared remote |
| Experiments | MLflow | Local service; production inference can use the DVC bundle independently |
| Delivery | Docker Compose, GitHub Actions, ECR, EC2 | AWS account; OIDC role for publishing; instance role for pulling |
| Monitoring | Prometheus and Grafana | Generated Grafana password; services remain private |
| HTTPS | Caddy and a domain pointing at EC2 | Domain optional for tunnel demo; needed for the documented public HTTPS path |

No OpenAI/LLM API key, paid job API, Kubernetes or GPU is required for the present MVP. Keep AWS access keys out of GitHub code, `.env.example`, frontend variables, screenshots and chat. Prefer SSO on the workstation and an instance role on EC2.

## Remaining stages for assessment

- [ ] Authenticate GitHub and push the local repository.
- [ ] Configure AWS account access and inspect costs/quotas for the chosen resources.
- [ ] Create/reuse private S3 storage, two ECR repositories, GitHub OIDC publishing role and EC2 read role/profile.
- [ ] Upload the DVC release to S3 and verify a fresh model-only pull.
- [ ] Configure the frontend origin and GitHub role/variables.
- [ ] Obtain a successful hosted CI/build/publish run; verify both ECR tags match one full Git SHA.
- [ ] Provision/install EC2 and deploy that SHA with the matching DVC bundle.
- [ ] Verify bundle identity and a real explained recommendation on EC2.
- [ ] Demonstrate private tunnel access or public HTTPS.
- [ ] Check monitoring, process restart recovery and backup/restore readiness.
- [ ] Capture the diagram-to-evidence mapping and disclose benchmark limitations.

Complete these before adding optional features. Their detailed commands and exit checks are in the other files in this directory.
