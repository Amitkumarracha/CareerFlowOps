# UI completion and demonstration guide

The portal has eleven main pages plus job details and a not-found page. It uses the existing API and persisted data; it does not generate demo job counts or model measurements in the browser.

| Page | Completed behavior |
| --- | --- |
| Overview `/` | Live jobs, API health, official-source cards and links into the candidate workflow |
| Discover `/jobs` | Keyword/location and advanced filters, pagination, shareable URL filters, Back navigation retains filters |
| Job details `/jobs/:id` | Description, skills, source occurrences, verification dates, official apply URL and persistent bookmark |
| For you `/recommended` | Profile-aware ranking, score filters, component explanations, missing skills, actual model/fallback identity; verified-bundle deployments serve the selected release only |
| Saved jobs `/saved` | Persistent shortlist, search and bookmark removal; application history is retained |
| Profile `/profile` | Editable extraction, normalized skills, validation, saved feedback, persistence across reloads and candidate-data deletion |
| Resume `/resume` | PDF/size validation, extraction feedback, latest 100 stored extraction summaries, on-demand text review and owner-checked deletion; deleting an extraction keeps edited profile |
| Applications `/applications` | Search and status filters, clickable status counts, manual updates/notes and timestamped history |
| Placement analytics `/tpo` | Real aggregate counts, distributions, skill gaps, candidate matches and disclosed sample bounds; admin token required |
| Model experiments `/mlops` | Saved validation/test results, split filter, selected-model highlight and evaluation JSON export; admin token required |
| Source health `/admin` | Live/snapshot ingestion, outcome feedback, polling, errors, provenance and linked possible-duplicate review; admin token required |
| System & guide `/system` | Live API/database readiness, verified bundle identity when configured, getting-started links, data/model and EC2 deployment lifecycles, stack and limitations |

Workspace access saves separate candidate/admin tokens in the tab session. Updating or disconnecting access cancels requests, clears cached workspace data and remounts the active page. It does not claim that saving a token validates it; protected endpoints validate access. Mobile navigation supports outside-click and Escape dismissal, expanded state and a skip-to-content link. Core controls have visible keyboard focus. Page titles follow the active route. Request failures can be retried and field validation/network errors use readable messages.

## Run the completed version

```bash
cd /home/amitkumar/Music/CareerFlowOps
export DOCKER_HOST=unix:///var/run/docker.sock
make setup                 # First checkout only; preserves an existing .env
make dev                   # Build and start Docker services
make monitoring
```

Already-built containers can be started without rebuilding:

```bash
docker compose --profile monitoring up -d --no-build --wait
docker compose ps
```

Open http://localhost:5173, http://localhost:5173/saved and http://localhost:5173/system. Docker's detached startup does not print Vite's clickable development URLs. These links are valid while the services are running. Use http://localhost:8000/docs for API contracts. Enter the local `.env` tokens through Workspace access; never put them in URLs or screenshots.

## Repeatable checks

```bash
make test
make lint
npm --prefix apps/web run build
# Optional isolated base-dependency environment, if created:
.venv-ci/bin/python -m pytest
# Validate the actual exported model:
.venv/bin/python -m pipelines.export_model --validate ml/artifacts/production
```

The completion review used Chromium with a temporary SQLite database, captured real ATS fixtures and a fictional verification candidate. It exercised access, profile save/reload, bookmark save/reload, search Back navigation, application update/filter, resume upload/review/delete, mobile navigation and disconnect. All 12 main route variants (including not-found) were checked at desktop width; all 11 main pages were checked at 390px and 320px without page-wide overflow. No JavaScript page errors occurred. Saved evaluation measurements came from existing local artifacts. Screenshots were visually inspected. Production PostgreSQL records were not modified by that browser test.

## Assessment evidence and remaining setup

The two supplied MLOps diagrams are represented in System & guide and in working delivery code: DVC preprocessing, three tracked experiments, metric-based selection, MLflow registration, a DVC release bundle, SHA-tagged images, EC2 model pull/validation, explained API predictions and container restart policies. The default remote remains local. AWS resources and hosted CI/ECR/EC2 execution require your local account setup and evidence; the UI labels this as prepared deployment code, not a verified cloud deployment.

See [the executable AWS runbook](../infra/aws/README.md) for S3, ECR, IAM/OIDC, GitHub variables, EC2, HTTPS and monitoring commands. No paid job API or LLM API is required for this implementation. Public ATS feeds and the public pretrained embedding model are sufficient; Hugging Face authentication is optional unless upstream access requires it.

Remaining product extensions are real multi-user accounts/roles, scheduled ingestion and closed-job expiry, OCR, human-validated larger evaluation data and scaling beyond the documented retrieval limits. These are outside the single-candidate MVP. Opening Apply never submits an application. Do not share a candidate token between unrelated people.

## Publish the local commits

Origin points at your supplied repository. The automated push could not authenticate. On this Arch Linux workstation, configure GitHub CLI yourself and then push:

```bash
sudo pacman -S github-cli
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
git push -u origin main
```

Keep tokens out of the remote URL and repository. A successful push starts GitHub checks/image builds; it does not prove the workflows passed. Inspect the Actions tab afterwards. ECR publishing additionally requires the OIDC role and repository variables in the AWS runbook.
