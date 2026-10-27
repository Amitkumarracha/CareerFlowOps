# Demo and viva guide

Prepared for the end-semester evaluation. Every statement here is backed by the repository or by the verification recorded in the [AWS deployment record](remaining/03_AWS_DEPLOYMENT.md#11-deployment-record-arjun-reddy-i-fork-27-october-2026). Where something is not implemented, this guide says so; say the same in the viva.

## 1. Rubric to evidence

| Rubric item | Marks | What to show |
| --- | --- | --- |
| CO1 Cloud services and MLOps fundamentals | 2 | AWS services working together: **S3** (DVC model remote), **ECR** (immutable images), **EC2** (host), **IAM with GitHub OIDC** (CI has no stored keys), **Systems Manager** (deployment and access without SSH), **Elastic IP and security group** (stable address, only ports 80 and 443 open) |
| CO2 ML pipeline design and CI/CD | 2 | DVC pipeline of seven stages (ingest, preprocess, build_training_set, train, evaluate, register, export_model); GitHub Actions run: checks, image build, ECR publish, automatic EC2 deploy |
| CO3 Model tracking, monitoring and optimization | 2 | MLflow experiment with 12 runs and a registry (`careerflowops-ranker`, alias `production` on version 4); three rankers compared on saved metrics; Prometheus and Grafana on the host; restart-policy recovery |
| CO4 Documentation, deployment strategy and presentation | 4 | This `docs/` folder, the two supplied diagrams, the runbook with a verified deployment record, teardown and rollback steps |
| Viva | 5 | Section 4 below |

## 2. Ten-minute demo script

Before you start: `powershell -ExecutionPolicy Bypass -File infra\aws\demo_access.ps1 status` must show Systems Manager `Online`. Keep the instance running (see section 5 if it was stopped).

1. **Architecture (1 min).** Show `mlops_pipeline_overview.png` then `ec2_deployment_flow.png`. One sentence each: data and models are versioned with DVC, experiments tracked with MLflow, the selected model is shipped to the server as a verified bundle, and code ships as an immutable Docker image.
2. **CI/CD (2 min).** Open the latest successful run in GitHub Actions. Point at: checks (lint, tests, migrations, frontend build, security audit), build, ECR publish through OIDC, deploy through Systems Manager.
3. **Registry and storage (1 min).** AWS console, region Asia Pacific (Mumbai): ECR repositories `careerflowops-api` and `careerflowops-web` with a tag equal to the Git commit SHA; S3 bucket `careerflowops-models-…` holding the DVC objects.
4. **Running service (2 min).** Open `https://15-252-197-53.sslip.io/ready`: it shows `status`, `model_version` and `bundle_id`. Explain that the server refuses to start with a missing or corrupt model instead of falling back silently.
5. **Client request and prediction (2 min).** In the portal, enter the candidate token (`demo_access.ps1 tokens`), open **For you** and show the score, its components, matched and missing skills, the explanation and the official apply link.
6. **Tracking and monitoring (2 min).** Run `demo_access.ps1 tunnels`. Show MLflow (`http://localhost:5000`): experiment, runs, the registered model. Then Prometheus (`http://localhost:19090`, status, targets) and Grafana (`http://localhost:13000`).

Optional, if asked about resilience: run the crash test from [operations section 4](remaining/04_OPERATIONS_AND_ASSESSMENT.md#4-monitoring-and-restart-verification) and show the API recovering by itself.

## 3. The pipeline in one paragraph

Public job-board data from official ATS endpoints (Greenhouse, Lever, Ashby) is ingested and normalized, keeping the raw payload and the source name, job ID, source URL and apply URL for every job. A DVC pipeline preprocesses it, builds a frozen training and evaluation set, trains three rankers (TF-IDF, a pretrained sentence-transformer and a hybrid), evaluates them, registers the result in MLflow and exports a self-contained model bundle with a manifest and checksums. The bundle is pushed to S3 through DVC. A push to `main` runs the checks, builds the API and web images tagged with the Git SHA, pushes them to ECR using short-lived OIDC credentials and deploys to EC2 through Systems Manager. The host pulls the image and the model, validates inference inside the published image, runs database migrations and only then starts the service. Docker restarts crashed containers.

## 4. Likely viva questions

**What is MLOps and why use it here?** Applying DevOps practice to machine learning so a model can be reproduced, delivered and monitored reliably. Here: versioned data and models, tracked experiments, automated build and deployment, and monitoring of the running service.

**DVC versus MLflow?** DVC versions large files and defines the reproducible pipeline (`dvc.yaml`, `dvc.lock`, S3 remote). MLflow records experiments (parameters, metrics, artifacts) and holds the model registry. Git stores code and the small pointers. They are complementary, not alternatives.

**Why immutable image tags tied to the Git SHA?** A deployed container can always be traced to one commit, and a tag can never be silently overwritten. Rollback means deploying an earlier SHA. The ECR repositories are configured with immutable tags, so pushing an existing tag is rejected.

**How does GitHub deploy to AWS without storing keys?** GitHub Actions presents a short-lived OIDC token; an IAM role trusts only this repository's `main` branch and exchanges it for temporary credentials. There are two roles: one that can only push to the two ECR repositories, and one that can only send a shell command to the tagged instance through Systems Manager.

**Why no SSH?** No open port 22 and no private key to protect or leak. Systems Manager gives audited command execution through IAM. The security group opens only 80 and 443.

**What exactly happens during a deployment?** Check the working tree and that the requested commit is still the tip of `main`; stop the API and web containers; pull both images; pull the model bundle from S3 with DVC; validate the model inside the published API image; start PostgreSQL and MLflow; start the API (which applies database migrations first) and web; compare the running bundle ID with the downloaded manifest. Any failed check stops the deployment.

**How do you roll back?** Deploy the previous commit SHA: its checkout restores the matching `dvc.lock`, so the matching image and model come together. State the limit honestly: database migrations are not rolled back automatically.

**What does the restart policy do?** `unless-stopped` restarts a container that exits unexpectedly and after a reboot. It does not restart a container someone stopped deliberately. Worth knowing: `docker kill` counts as a manual stop, so the test kills the server process inside the container instead. It also does not detect a process that is alive but unhealthy.

**Why EC2 and not SageMaker, Lambda or Kubernetes?** The system is a small stateful stack (API, web, PostgreSQL, MLflow, monitoring) for a single-host MVP, and the project rules exclude Kubernetes and microservices. EC2 with Compose is the simplest thing that is reproducible. For scale, ECS or EKS and RDS would be the next step.

**How is the model monitored?** The API exports Prometheus metrics (request counts and latency, inference time, ingestion runs and duplicates). Prometheus scrapes it, four alert rules cover an unreachable API, failed readiness, sustained server errors and failed ingestion, and Grafana shows a provisioned dashboard. Not implemented: notification delivery (no receiver is configured), host or disk metrics and statistical drift detection.

**How would you detect drift?** Compare the distribution of incoming resume and job features and the score distribution against the training set (for example with Evidently) and alert on a threshold. This is a documented extension; it is not built.

**How good is the model?** Be precise: the benchmark is six fictional queries against 29 frozen real jobs with illustrative labels written during development, not human-validated. The selection key is validation nDCG@5, then Precision@5, then the algorithm name (`pipelines/evaluate.py`). All three rankers tie at 1.0 on the first two, so the name decides and TF-IDF wins. Say this openly: the benchmark is too small to separate them. TF-IDF was also the fastest in the saved runs (about 27 ms against 29 and 31 ms), but latency is not part of the selection. The hybrid ranker scored 0.7426 nDCG@5 on the held-out test queries. These numbers show the pipeline works; they are not a claim of production accuracy.

**Why does every prediction include an explanation?** A hiring-related ranking must be inspectable. Each result carries semantic, skill, eligibility, location and freshness scores, matched and missing skills and a text explanation, plus the model version and any fallback reason (null in production).

**Security and compliance choices?** No secrets in Git (generated on the host); separate candidate and admin tokens; production refuses weak tokens, SQLite, a missing model and non-HTTPS CORS origins; IMDSv2 required; databases and dashboards bound to loopback only; only official public job endpoints are used; applications are never submitted automatically, the user opens the official apply link.

**What went wrong during setup and how was it fixed?** Good question to volunteer. The account's Free plan rejected the planned instance type, so a free-tier-eligible 8 GiB type was used. GitHub's immutable OIDC subject format did not match the trust policy, so both formats were allowed. The production CORS guard rejected a plain HTTP origin, so the site is served over HTTPS rather than weakening the guard. `docker kill` did not trigger the restart policy, so the test was corrected. All four are recorded in the deployment record.

**What would you improve next?** Per-user accounts and roles (today one demo candidate token), notification delivery for alerts, drift monitoring, an infrastructure-as-code definition of the AWS resources, off-host backups with retention, and zero-downtime releases.

**What does it cost and how is it removed?** A single instance, an Elastic IP, ECR and S3 storage. The teardown list is at the end of the deployment record.

## 5. Day-of checklist

- `demo_access.ps1 status`: instance `running`, Systems Manager `Online`, URL printed. If the instance was stopped, start it with `aws ec2 start-instances --instance-ids <id> --profile careerflow --region ap-south-1`, wait two minutes and check `/ready`. The containers have restart policies and Docker starts at boot, but a full stop and start was not tested, so check early rather than during the evaluation.
- Open in tabs beforehand: the site, `/ready`, the GitHub Actions run, ECR and S3 consoles (region Mumbai), the diagrams.
- Run `tokens` once, paste the candidate token into the portal and do not show the terminal on screen.
- Install the Session Manager plugin before the evaluation (`winget install Amazon.SessionManagerPlugin`) and test `tunnels` once.
- Keep a plan for no internet: the repository documentation and the saved evidence in the deployment record still tell the whole story.
