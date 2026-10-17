# Local checks, Git, DVC and release publishing

Run workstation blocks from `/home/amitkumar/Music/CareerFlowOps`. Cloud commands here are instructions for you; they were not executed while writing the guide.

## 1. Local preflight

WORKSTATION — inspect the existing setup without rebuilding large images:

```bash
cd /home/amitkumar/Music/CareerFlowOps
export DOCKER_HOST=unix:///var/run/docker.sock
git status --short
git remote -v
df -h .
docker compose --profile monitoring up -d --no-build --wait
docker compose ps
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/ready
```

The current checkout already has environments and images. On a **fresh checkout only**, after providing adequate disk and installing Docker/Compose, Make, Node 22.18+ and Python:

On a fresh Arch workstation, the system packages and Docker access can be prepared with:

```bash
sudo pacman -S --needed python nodejs npm make docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out/in if Docker group membership was just changed, then return to the repository. Use the Docker daemon already installed if the machine already has one; do not reinstall it to start existing containers.

```bash
make setup
make dev
make monitoring
```

`make setup` creates/preserves the ignored `.env` and installs the base development dependencies. `make ml-setup` separately installs the larger ML environment. `make cloud-setup` installs DVC/S3 into a separate `.venv-deploy`. Do not run all three repeatedly just to start the UI.

Run the project checks:

```bash
make test
make lint
npm --prefix apps/web run build
```

Expected: passing backend/frontend tests, Ruff, TypeScript, ESLint, Prettier and a production web build. Test counts can increase after future work. Database migration checks, when PostgreSQL is running:

```bash
make db-migrate
.venv/bin/python infra/scripts/host.py .venv/bin/alembic -c apps/api/alembic.ini check
```

Open http://localhost:5173. Workspace access uses the candidate/admin tokens from your local `.env`. Do not paste them into chat. API contracts: http://localhost:8000/docs.

## 2. Authenticate Git

WORKSTATION — Arch Linux; install GitHub CLI if absent:

```bash
sudo pacman -S --needed git github-cli
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git
gh auth status
git remote -v
```

Origin is already configured. Only if it is missing:

```bash
git remote add origin https://github.com/Amitkumarracha/CareerFlowOps.git
```

Inspect remote state before publishing:

```bash
git fetch origin
git branch -r
git log -5 --oneline
```

If `origin/main` exists and push is rejected, inspect `git log --oneline --left-right main...origin/main` and reconcile the actual changes. Do not force-push over someone else's work. Do not place a token in the remote URL. GitHub authentication does not configure AWS access.

The additional `workflow` scope supports publishing the repository's Actions workflow files. For an already configured OAuth login that lacks it, use `gh auth refresh --hostname github.com --scopes workflow`. A fine-grained token instead needs the appropriate repository contents/workflows permissions. See [GitHub CLI authentication](https://cli.github.com/manual/gh_auth_login).

## 3. Understand the model pipeline

| Stage | Entry point | Main output |
| --- | --- | --- |
| ingest | `pipelines.ingest --fixtures --export ...` | Frozen raw public ATS snapshot |
| preprocess | `pipelines.preprocess` | Normalized job dataset |
| build_training_set | `pipelines.build_training_set` | Frozen corpus/query splits and labels |
| train | `pipelines.train` | Fitted TF-IDF vocabulary, pinned transformer, embeddings, training/run metadata |
| evaluate | `pipelines.evaluate` | Measured validation/test metrics and selected algorithm |
| register | `pipelines.register` | MLflow model version/production alias and metadata |
| export_model | `pipelines.export_model` | Self-contained `ml/artifacts/production` bundle for DVC delivery |

Git stores code, small public samples, parameters, `dvc.yaml` and `dvc.lock`. DVC stores larger cached data/models. MLflow stores run history, measured metrics and model aliases. ECR stores executable API/web images. These are separate responsibilities.

The deployed API fetches no model from the internet on a prediction request in bundle mode. The EC2 deployment pulls it from DVC before startup, then the API loads and validates the read-only bundle. EC2 does not train. A TF-IDF release needs its fitted vectorizer and metadata; semantic/hybrid releases also include the local transformer.

### Existing successful artifacts and the existing MLflow server

The selected release already exists in this workspace. Validate it:

```bash
.venv/bin/python -m pipelines.export_model --validate ml/artifacts/production
.venv/bin/dvc status export_model
.venv/bin/dvc dag
```

If you deliberately changed export code/metadata, regenerate the export stage without rerunning training:

```bash
.venv/bin/python infra/scripts/host.py .venv/bin/dvc repro --single-item export_model
.venv/bin/dvc push -r storage
```

### New experiment, scoring/data change or fresh training machine

Start PostgreSQL/MLflow, then install the ML dependencies once:

```bash
make ml-setup
make reproduce
```

`make reproduce` runs the seven stages and pushes to the configured default local remote. It does not publish S3 by itself. Initial semantic-model setup requires internet access to the pinned public model revision.

If you use an **empty/different MLflow backend with cached training outputs**, the recorded run IDs will not exist there. Explicitly rerun the full pipeline to create new runs:

```bash
.venv/bin/python infra/scripts/host.py .venv/bin/dvc repro --force
.venv/bin/dvc push -r storage
```

This performs real indexing/evaluation/registration and changes artifacts. Run it on the training workstation, not EC2. Never copy someone else's metrics into the experiment UI to make it appear complete. Never add private resumes to DVC.

## 4. Configure production DVC storage

First finish [AWS sections 2–4](03_AWS_DEPLOYMENT.md#2-workstation-aws-access). In the same authenticated workstation shell:

```bash
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export MODEL_BUCKET="careerflowops-models-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export DVC_REMOTE_URL="s3://$MODEL_BUCKET/careerflowops"
make cloud-setup
.venv-deploy/bin/dvc remote add --local --force production "$DVC_REMOTE_URL"
.venv-deploy/bin/dvc remote list
.venv-deploy/bin/dvc push -r production
.venv-deploy/bin/dvc status -c -r production ml/artifacts/production
aws s3 ls "s3://$MODEL_BUCKET/careerflowops/" --recursive --summarize
```

The workstation AWS identity needs S3 read/write permissions for this prefix. The rendered `trainer-storage.json` describes that permission scope; your AWS administrator must grant it to the existing training identity if needed. The GitHub ECR role and EC2 read-only role are intentionally insufficient for training uploads.

`--local` records the remote in ignored `.dvc/config.local`. Credentials come from the AWS provider chain, not the DVC configuration. Keep the committed default `storage` local remote for offline demos; explicitly use `-r production` for S3.

**Exit check:** no missing release objects in DVC status and a successful fresh model-only pull in the next section. An S3 listing alone does not prove the correct release can load.

## 5. Verify a fresh model-only pull and commit its pointer

WORKSTATION — this creates a disposable DVC workspace and validates the pulled release using this checkout's installed inference code. It does not mutate the live database:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from ml.inference.bundle import load_bundle

root = Path.cwd()
dvc = str(root / '.venv-deploy/bin/dvc')
with tempfile.TemporaryDirectory(prefix='careerflowops-release-check-') as temporary:
    folder = Path(temporary)
    for name in ['dvc.yaml', 'dvc.lock']:
        shutil.copy2(root / name, folder / name)
    commands = [
        ['init', '--no-scm'],
        ['remote', 'add', 'production', os.environ['DVC_REMOTE_URL']],
        ['pull', '-r', 'production', 'ml/artifacts/production'],
    ]
    for command in commands:
        subprocess.run([dvc, *command], cwd=folder, check=True)
    bundle = load_bundle(str(folder / 'ml/artifacts/production'))
    print({'bundle_id': bundle.bundle_id, 'model_version': bundle.config['model_version']})
PY
```

Now review and commit actual model-pointer changes. A successful S3 upload alone usually does not change tracked files; skip the commit if nothing changed:

```bash
git status --short
git diff -- dvc.yaml dvc.lock params.yaml
git add dvc.yaml dvc.lock params.yaml
if ! git diff --cached --quiet; then
  git commit -m "ml: version evaluated production model release"
fi
```

Other reviewed source/documentation changes must also be committed before selecting the release SHA. Do not `git add -f` ignored models, `.env`, DVC caches or backups. Protect `main` and use pull requests for future feature changes once the initial project is published.

See the official [DVC pull reference](https://doc.dvc.org/command-reference/pull) and [reproduction reference](https://doc.dvc.org/command-reference/repro) for target selection and reproduction flags.

## 6. Configure GitHub Actions and publish

WORKSTATION — the roles and ECR repositories must already exist. Choose the browser API origin before this step:

- Private SSH demo: `http://localhost:18000` and tunnel local ports 18000/15173 to EC2 API/frontend ports 8000/5173.
- Public HTTPS: `https://<your-domain>` and use the Caddy edge configuration.

```bash
export GH_REPO=Amitkumarracha/CareerFlowOps
export AWS_REGION=ap-south-1
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export BROWSER_API_ORIGIN=http://localhost:18000
# Public alternative: export BROWSER_API_ORIGIN=https://<your-domain>
gh secret set AWS_ROLE_ARN --repo "$GH_REPO" --body "arn:aws:iam::$AWS_ACCOUNT_ID:role/CareerFlowOpsGitHubPublish"
gh variable set AWS_REGION --repo "$GH_REPO" --body "$AWS_REGION"
gh variable set AWS_ECR_REPOSITORY --repo "$GH_REPO" --body careerflowops-api
gh variable set AWS_ECR_WEB_REPOSITORY --repo "$GH_REPO" --body careerflowops-web
gh variable set VITE_API_BASE_URL --repo "$GH_REPO" --body "$BROWSER_API_ORIGIN"
gh variable list --repo "$GH_REPO"
git status --short
git push -u origin main
```

The role ARN is an account identifier, not an access key; the workflow's existing input is named `AWS_ROLE_ARN` in GitHub Secrets. It obtains short-lived credentials through OIDC. See [GitHub CLI variables](https://cli.github.com/manual/gh_variable_set) and [secrets](https://cli.github.com/manual/gh_secret_set).

If the current SHA was already published and the API origin/configuration changed, create a **new release SHA** after reviewing the new variables:

```bash
git commit --allow-empty -m "deploy: publish release with updated deployment configuration"
git push origin main
```

This intentionally changes the image tag. Do not rerun an already-published immutable tag to replace its image contents. A failed partial publish can also require a new release commit because one repository's tag may already exist.

## 7. Confirm hosted checks and both ECR images

WORKSTATION:

```bash
export RELEASE_SHA="$(git rev-parse HEAD)"
gh run list --repo "$GH_REPO" --workflow docker-publish.yml --commit "$RELEASE_SHA"
export BUILD_RUN_ID='<run-id-from-the-list>'
gh run watch "$BUILD_RUN_ID" --repo "$GH_REPO" --exit-status
gh run view "$BUILD_RUN_ID" --repo "$GH_REPO"
aws ecr describe-images --repository-name careerflowops-api --image-ids "imageTag=$RELEASE_SHA" --query 'imageDetails[0].{tags:imageTags,digest:imageDigest}'
aws ecr describe-images --repository-name careerflowops-web --image-ids "imageTag=$RELEASE_SHA" --query 'imageDetails[0].{tags:imageTags,digest:imageDigest}'
```

Use the full 40-character commit SHA, not `main`, `latest`, the MLflow model version or the dataset hash. The workflow first runs reusable CI, then builds API/web images, then optionally publishes ECR. A green build with the AWS step skipped is not evidence of an ECR push. GitHub Actions does not currently SSH to EC2 or deploy automatically.

For a first run that built without AWS configuration and never published tags, you can dispatch the same branch after adding the role:

```bash
gh workflow run docker-publish.yml --repo "$GH_REPO" --ref main
```

Inspect the resulting run and both ECR repositories again. The [run-list reference](https://cli.github.com/manual/gh_run_list) documents commit/workflow filtering.

**Exit check:** successful hosted checks, successful ECR publishing steps, both images tagged with `RELEASE_SHA`, S3 model objects present and the matching `dvc.lock` in that exact Git commit. Continue to [EC2 creation](03_AWS_DEPLOYMENT.md#5-create-an-ec2-instance).

## 8. Normal future release sequence

1. Change a feature on a branch; add meaningful tests and update its docs.
2. Run local checks. If data/scoring changed, reproduce and evaluate; inspect held-out metrics.
3. Push the new DVC objects to S3 **before** publishing a Git pointer that depends on them.
4. Merge reviewed changes and run CI/build/publish with a new SHA.
5. Back up EC2 before migrations, then deploy that exact SHA using the AWS guide.
6. Verify readiness, model identity, explained predictions, monitoring and user flows.
7. Record the deployed SHA, image digests and model bundle ID for rollback.

There is no automatic retraining-on-ingestion or automatic EC2 deployment in the current code. Those remain separately planned improvements.
