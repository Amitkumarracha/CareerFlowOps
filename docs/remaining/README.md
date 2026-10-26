# CareerFlowOps: remaining work and execution order

Reviewed: **26 October 2026**. Repository: `Amitkumarracha/CareerFlowOps`.

Start with [the production handover](06_PRODUCTION_HANDOVER.md) for the latest local backup/restore evidence, tested operations commands, optional schedules and account inputs still needed for a live deployment.

For the new repeatable terminal commands and automatic release path, start with [the presentation guide](../PRESENTATION.md). [Automatic EC2 deployment](../AUTOMATIC_DEPLOYMENT.md) is now implemented behind explicit repository configuration; AWS execution still requires your account/host setup.

The local single-candidate MVP, GitHub synchronization and hosted CI are verified. Remaining assessment-critical work includes moving DVC artifacts to S3, publishing images to ECR, deploying the matching release to EC2, and collecting cloud evidence. Cloud configuration files alone do not prove a cloud deployment.

## Read these files

| File | Contents |
| --- | --- |
| [01_OVERALL_PROGRESS.md](01_OVERALL_PROGRESS.md) | Completed functionality, verified evidence, exact limitations, stack and API requirements |
| [02_GIT_DVC_RELEASE.md](02_GIT_DVC_RELEASE.md) | Local commands, Git authentication, model reproduction, S3 DVC push/pull, release commits, GitHub Actions and ECR verification |
| [03_AWS_DEPLOYMENT.md](03_AWS_DEPLOYMENT.md) | AWS login, S3/ECR/IAM/OIDC, EC2 creation, Ubuntu installation, deployment, private demo and public HTTPS |
| [04_OPERATIONS_AND_ASSESSMENT.md](04_OPERATIONS_AND_ASSESSMENT.md) | End-to-end smoke check, monitoring, backups, restore/rollback, troubleshooting, assessment checklist and shutdown |
| [05_FEATURE_IMPROVEMENTS.md](05_FEATURE_IMPROVEMENTS.md) | Prioritized future features, technical changes, dependencies and acceptance criteria |
| [06_PRODUCTION_HANDOVER.md](06_PRODUCTION_HANDOVER.md) | Latest operations implementation/evidence, schedules, production configuration and required account inputs |

## Follow this order

| Stage | Task | Where | Completion condition |
| --- | --- | --- | --- |
| 0 | Read the current progress and limits | [Progress](01_OVERALL_PROGRESS.md) | Understand what already exists |
| 1 | Check disk, local services and tests | [Git/DVC section 1](02_GIT_DVC_RELEASE.md#1-local-preflight) | Working local portal and passing checks |
| 2 | Install/login to GitHub CLI | [Git/DVC section 2](02_GIT_DVC_RELEASE.md#2-authenticate-git) | Authenticated push access; no force push |
| 3 | Select private tunnel or public HTTPS | [AWS section 1](03_AWS_DEPLOYMENT.md#1-choose-the-demonstration-mode) | Browser API origin chosen before building images |
| 4 | Configure AWS account, bucket, ECR and roles | [AWS sections 2–4](03_AWS_DEPLOYMENT.md#2-workstation-aws-access) | S3 storage, two image repositories, GitHub role and EC2 instance profile exist |
| 5 | Validate/export the selected model and push to S3 | [Git/DVC sections 3–5](02_GIT_DVC_RELEASE.md#3-understand-the-model-pipeline) | Selected release exists in the remote, with the correct Git/DVC pointer |
| 6 | Configure GitHub variables and publish release | [Git/DVC sections 6–7](02_GIT_DVC_RELEASE.md#6-configure-github-actions-and-publish) | Hosted CI passes; both ECR images have the same full commit SHA |
| 7 | Provision EC2 and install tools | [AWS sections 5–6](03_AWS_DEPLOYMENT.md#5-create-an-ec2-instance) | Reachable x86-64 Ubuntu host with instance role and Docker |
| 8 | Deploy exact Git SHA, image tags and DVC model | [AWS section 7](03_AWS_DEPLOYMENT.md#7-deploy-the-exact-release) | `/ready` identifies the expected model bundle |
| 9 | Open tunnel or configure DNS/TLS | [AWS sections 8–9](03_AWS_DEPLOYMENT.md#8-private-demonstration-with-ssh-tunnels) | Portal reaches the EC2 API from your browser |
| 10 | Verify application, monitoring and restart behavior | [Operations](04_OPERATIONS_AND_ASSESSMENT.md) | Real explained predictions and application history; monitoring works |
| 11 | Back up and collect assessment evidence | [Operations](04_OPERATIONS_AND_ASSESSMENT.md) | Restorable backup and screenshots/log evidence without credentials |
| 12 | Add product improvements in priority order | [Roadmap](05_FEATURE_IMPROVEMENTS.md) | Separate milestones with tests and measurable outcomes |

Do not rerun the whole training pipeline just to deploy an already validated bundle. Do not publish an image before deciding its browser-facing API URL. Do not select a release SHA until model-pointer changes are committed. Never overwrite immutable ECR tags; use a new commit when configuration changes.

## Command conventions

- **WORKSTATION** means your Arch Linux laptop. The existing checkout is `/home/amitkumar/Music/CareerFlowOps`.
- **EC2** means an SSH terminal on the Ubuntu instance, normally `~/CareerFlowOps`.
- Run each fenced block in its indicated terminal. Exports do not automatically transfer to another terminal or server; re-enter the relevant variable block after reconnecting.
- Replace `<placeholders>` before running a block. They are not valid account IDs, domains or release SHAs.
- AWS creation/start commands incur account usage. They are documented for you to run; writing this guide did not execute them.
- `ops-private/` is ignored by Git for private backups and operator files. `.env`, `.aws-policies/`, model binaries and local DVC storage also stay out of Git.
- Inspect command errors. Existing resources should be inspected/reused, not blindly recreated. Do not hide failures with `|| true`.

## What is required versus optional

**Required to finish the cloud assessment:** GitHub authentication; passing hosted workflows; S3 DVC objects; ECR images; an EC2 instance with a matching release; verified API/model readiness; explained predictions; monitoring and evidence.

**Optional for a private assessment demo:** a domain, public HTTPS, email integration, paid job APIs and additional ML libraries. An SSH tunnel can demonstrate the full EC2 deployment without exposing the app publicly.

**Required before a real shared student rollout:** real per-user authentication and TPO roles, ownership/isolation tests, scheduled source freshness, backup/restore practice, sufficient representative evaluation and a privacy/retention policy. The present candidate token maps to one server-owned identity.

## First commands today

WORKSTATION — these inspect/start the existing local stack; they do not deploy AWS:

```bash
cd /home/amitkumar/Music/CareerFlowOps
export DOCKER_HOST=unix:///var/run/docker.sock
git status --short
df -h .
docker compose --profile monitoring up -d --no-build --wait
curl --fail http://localhost:8000/ready
```

Open http://localhost:5173, then follow stage 1. All later commands are in the linked files.
