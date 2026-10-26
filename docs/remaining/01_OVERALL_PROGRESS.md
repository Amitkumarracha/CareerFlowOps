# Overall progress, requirements and known gaps

Reviewed: **26 October 2026**. This is an evidence-based status report, not a completion percentage. The historical implementation log remains in [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md). Repeatable commands are in [the terminal presentation guide](../PRESENTATION.md).

Latest operations verification: 85 backend/13 frontend tests passed; real private backup and isolated database restore passed; 1,064 postings normalized during live ingestion. Production configuration guards, tested alert rules and optional ingestion/backup timer units are implemented. AWS access, shared-user identity, enabled EC2 schedules, off-host backups and notification delivery remain pending. See [production handover](06_PRODUCTION_HANDOVER.md).

## Current result

The application and MLOps release path are implemented and tested. GitHub authentication and the first repository synchronization succeeded on 25 October. A real hosted workflow passed backend/frontend checks and built both images. AWS resources/credentials are still unconfigured, so ECR publication, S3 remote execution and EC2 deployment have not been demonstrated. Their workflow steps remain explicitly disabled/skipped until configuration exists.

Current runtime checks during this review:

| Check | Observed result |
| --- | --- |
| API health and readiness | HTTP 200 at port 8000 |
| Local jobs endpoint | 1,148 canonical records after the 26 October refresh; historical records remain until a future verified-expiry feature |
| Docker services | API, web, PostgreSQL, MLflow, Prometheus and Grafana running |
| Current readiness mode | Verified bundle mode locally; still not proof of EC2 hosting |
| Selected model artifact | TF-IDF, `b3e854956e87-574536b6` |
| Saved MLflow registry metadata | `careerflowops-ranker@production`, version 4 |
| Exported DVC production bundle | Present locally |
| Git implementation commits | Training source checkpoint `574536b`; published model pointer `60ea401`; use `git rev-parse HEAD` for the latest release |
| Workstation prerequisites | Authenticated GitHub CLI is in `.venv-tools/bin/gh`; AWS CLI/account configuration remains outstanding |
| Available disk | Disk headroom was restored before this run; a full clean API/web Docker build succeeded |

Do not delete project databases, volumes, artifacts or unrelated caches to free space. Choose storage deliberately before large builds. Image publishing can run on a GitHub-hosted runner once access is configured.

## Completed functionality

| Area | Implemented | Remaining boundary |
| --- | --- | --- |
| React portal | Overview, search, job details, recommendations, saved jobs, profile, resume, applications, TPO, experiments, source health, system guide, not-found view | Continue accessibility and real-user usability review |
| Search | Keyword, location, company, source, work arrangement, employment, experience and posting-date filters; URL state and pagination | Recommendation retrieval still examines at most 1,000 recent active jobs |
| ATS ingestion | Greenhouse, Lever and Ashby adapters, bounded retries, allowlisted boards, live/snapshot modes and optional systemd schedules | Enable/verify the EC2 schedule; expiry/revalidation and more employer boards |
| Data quality | Raw payloads separate from normalized jobs, idempotent upserts, source occurrences and preserved apply URLs | Fuzzy matches are suggestions; no merge/reject review workflow |
| Resume/profile | Text PDF extraction, known-skill normalization, editable profile, history/text review and owner-checked deletion | No OCR or broad entity-recognition model |
| Ranking | TF-IDF, pretrained SentenceTransformer and hybrid; component scores and explanations | Human-validated larger benchmark; no claim of hiring probability |
| Applications | Persistent bookmarks, official Apply, six manual states, notes/history, search/status filters | No reminders, calendar integration or automatic submission |
| TPO | Actual aggregate counts, distributions, potential matches and disclosed sample limits | A real cohort model and per-user roles are absent |
| MLflow | Actual experiment runs, metrics/artifacts, model versions and production alias | Local backend/artifacts are not automatically replicated to a new EC2 host |
| DVC | Seven stages and a self-contained selected-model bundle, local push and fresh isolated pull verified | Production S3 remote must be configured and populated |
| Production serving | File/inference compatibility validation, prediction probe, fail-closed bundle inference, readiness identity | Must execute the EC2 deployment and verify the downloaded release there |
| Containers | Clean API/web image builds, Compose, migrations, persistence and restart policies | Cloud images still need the configured ECR account |
| CI/CD | Hosted checks/build passed; SHA-tagged builds, optional OIDC ECR publishing and configured SSM deployment | AWS execution remains unverified and disabled until roles/host exist |
| Monitoring | Prometheus metrics, structured HTTP logs, Grafana dashboard and tested alert rules | Notification delivery, host/disk metrics, SLO enforcement and ML drift |
| Access/privacy | Separate candidate/admin bearer tokens, private candidate endpoints and cache clearing on disconnect | Candidate token identifies one candidate; not a multi-user platform |

## Verification already performed

Before the 25 October completion, the recorded verification included:

- 44 backend tests in the base dependency environment; one upstream Starlette/httpx deprecation warning.
- 13 frontend tests, strict TypeScript, ESLint, Prettier, Ruff and a Vite production build.
- Chromium candidate flows using a temporary SQLite database: access, profile save/reload, saved-job persistence, search Back navigation, application changes/filtering, resume upload/review/delete, mobile navigation and disconnect.
- Twelve main route variants, a job-detail flow, mobile widths of 390px and 320px, with no page-wide overflow or JavaScript page errors observed.
- Actual model export, local DVC push, fresh isolated DVC pull, bundle inference, API readiness/prediction and validation inside the API image.
- Fake-tool deployment tests: invalid models prevent service startup. These test the deployment control flow; they do not substitute for real AWS execution.

The earlier documentation-only update did not rerun application tests. The 25 October execution below supersedes that limitation; no AWS resources were provisioned. Use [the commands guide](02_GIT_DVC_RELEASE.md) for repeatable checks.

The 25 October completion additionally passed 63 backend and 13 frontend tests, reran the full DVC pipeline, created three new measured MLflow runs and production version 4, validated a fresh DVC pull and explained inference against the running bundle, completed clean Docker builds and refreshed real ATS data (1,062 fetched; 719 Greenhouse, 309 Lever, 34 Ashby; no source errors). Hosted run [40156338814](https://github.com/Amitkumarracha/CareerFlowOps/actions/runs/40156338814) passed checks and Docker builds; AWS-dependent steps were skipped. Future release results should be checked directly in Actions rather than assumed from this snapshot.

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

- [x] Authenticate GitHub and push the local repository.
- [ ] Configure AWS account access and inspect costs/quotas for the chosen resources.
- [ ] Create/reuse private S3 storage, two ECR repositories, GitHub OIDC publishing role and EC2 read role/profile.
- [ ] Upload the DVC release to S3 and verify a fresh model-only pull.
- [ ] Configure the frontend origin and GitHub role/variables.
- [x] Obtain a successful hosted CI and Docker build run.
- [ ] Configure ECR publishing and verify both ECR tags match one full Git SHA.
- [ ] Provision/install EC2 and deploy that SHA with the matching DVC bundle.
- [ ] Verify bundle identity and a real explained recommendation on EC2.
- [ ] Demonstrate private tunnel access or public HTTPS.
- [ ] Check monitoring, process restart recovery and backup/restore readiness.
- [ ] Capture the diagram-to-evidence mapping and disclose benchmark limitations.

Complete these before adding optional features. Their detailed commands and exit checks are in the other files in this directory.
