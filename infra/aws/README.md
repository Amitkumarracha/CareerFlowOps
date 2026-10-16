# AWS ECR + S3 + EC2 runbook

The deployment code is implemented; AWS provisioning, publishing and hosting must be executed by you. No AWS resources were created from this workspace. Commands below target your supplied repository and the standard AWS partition. Review your account and expected costs before running resource-creation commands.

## 1. Tools and account access (your workstation)

Install AWS CLI v2, Git, Docker Compose, Python 3.12 and Node 22.18+. On Arch Linux, use your package manager for `aws-cli-v2`, Docker/Compose, Node/npm and Python. This project uses uv to supply Python 3.12 when the system version differs. Configure AWS access with SSO or your existing local AWS profile; never paste keys into chat or Git.

```bash
cd /home/amitkumar/Music/CareerFlowOps
export DOCKER_HOST=unix:///var/run/docker.sock
aws configure sso
aws sso login
aws sts get-caller-identity
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export MODEL_BUCKET="careerflowops-models-${AWS_ACCOUNT_ID}-${AWS_REGION}"
python3 infra/aws/policies.py --account "$AWS_ACCOUNT_ID" --region "$AWS_REGION" --bucket "$MODEL_BUCKET"
make cloud-setup
```

For a named SSO profile, export `AWS_PROFILE` before login. `.aws-policies/` is ignored; generated documents contain account identifiers, not credentials. The code never invokes AWS while generating these files.

## 2. Create storage and image repositories (run once)

```bash
aws s3api create-bucket --bucket "$MODEL_BUCKET" --region "$AWS_REGION" --create-bucket-configuration "LocationConstraint=$AWS_REGION"
aws s3api put-public-access-block --bucket "$MODEL_BUCKET" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$MODEL_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$MODEL_BUCKET" --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws ecr create-repository --repository-name careerflowops-api --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name careerflowops-web --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true
```

The bucket command assumes `ap-south-1`; for `us-east-1`, omit `--create-bucket-configuration`. Existing resources should be inspected/reused rather than recreated. Restrict the training identity to the generated `trainer-storage.json` policy for this prefix; EC2 needs only read access. The training identity also needs your normal MLflow/PostgreSQL access, which is local for this demo.

## 3. GitHub OIDC and EC2 IAM roles (run once)

Check whether your account already has the GitHub provider. Reuse it if present:

```bash
aws iam list-open-id-connect-providers
# Run this only if token.actions.githubusercontent.com is absent:
aws iam create-open-id-connect-provider --url https://token.actions.githubusercontent.com --client-id-list sts.amazonaws.com
aws iam create-role --role-name CareerFlowOpsGitHubPublish --assume-role-policy-document file://.aws-policies/github-trust.json
aws iam put-role-policy --role-name CareerFlowOpsGitHubPublish --policy-name CareerFlowOpsECR --policy-document file://.aws-policies/github-ecr.json
aws iam create-role --role-name CareerFlowOpsEC2 --assume-role-policy-document file://.aws-policies/ec2-trust.json
aws iam put-role-policy --role-name CareerFlowOpsEC2 --policy-name CareerFlowOpsPull --policy-document file://.aws-policies/ec2-pull.json
aws iam create-instance-profile --instance-profile-name CareerFlowOpsEC2
aws iam add-role-to-instance-profile --instance-profile-name CareerFlowOpsEC2 --role-name CareerFlowOpsEC2
```

The GitHub trust policy permits only `Amitkumarracha/CareerFlowOps` on `main`. Do not broaden it to arbitrary repositories. The EC2 role can pull the two ECR repositories and read only `s3://$MODEL_BUCKET/careerflowops/`; it cannot publish images or models. If you use Systems Manager, attach the AWS-managed SSM instance policy separately. Do not run `dvc gc --cloud` on shared storage without a retention policy.

In GitHub repository **Settings → Secrets and variables → Actions**, configure:

| Kind | Name | Value |
| --- | --- | --- |
| Secret | `AWS_ROLE_ARN` | `arn:aws:iam::<your-account-id>:role/CareerFlowOpsGitHubPublish` |
| Variable | `AWS_REGION` | `ap-south-1` |
| Variable | `AWS_ECR_REPOSITORY` | `careerflowops-api` |
| Variable | `AWS_ECR_WEB_REPOSITORY` | `careerflowops-web` |
| Variable | `VITE_API_BASE_URL` | `https://<your-domain>` for the Caddy deployment |

No AWS access-key secret is required. Main runs CI and builds images; ECR publishing is skipped until the role is configured. Publishing does not deploy EC2 automatically. Use a fresh commit after changing the frontend origin: immutable image tags cannot be overwritten by rerunning a published SHA.

## 4. Publish the evaluated model (training workstation)

Start PostgreSQL/MLflow and reproduce if artifacts do not exist. For an existing successful evaluation/registration, only the export stage is needed:

```bash
make ml-setup
# Full training/indexing/evaluation/registration/export when needed:
make reproduce
# Or export the existing evaluated production run:
.venv/bin/python infra/scripts/host.py .venv/bin/dvc repro --single-item export_model
.venv-deploy/bin/dvc remote add --local --force production "s3://$MODEL_BUCKET/careerflowops"
.venv-deploy/bin/dvc push -r production
# Commit the release pointer, never the model files or credentials:
git add dvc.yaml dvc.lock
git commit -m "ml: publish evaluated model release pointer"
git push origin main
```

`make reproduce` pushes to the default local remote; the explicit `push -r production` copies cached data/models to S3. Keep the entire `dvc.lock` associated with a release. EC2 pulls `ml/artifacts/production` only and does not retrain. A TF-IDF selection ships the fitted vectorizer and metadata; a semantic/hybrid selection additionally ships the pinned transformer weights. MLflow retains experiment/alias management; DVC delivers the deployable artifact. Do not version private candidate data.

## 5. Prepare EC2 (your AWS console, then SSH)

Use x86-64 Ubuntu 24.04, the `CareerFlowOpsEC2` instance profile, enough RAM for all chosen services and sufficient disk for old/new inference images. For the full stack, allow at least 8 GB RAM and 30 GB free disk, then measure usage and adjust. These are capacity starting points, not a price estimate. Restrict SSH to your IP; allow 80/443 only for the public TLS endpoint. Keep 5432/5000/3000/9090/8000/5173 private.

Install Docker Engine with its Compose plugin, Git, Python 3.12/venv, curl and AWS CLI v2 using their official installers. Enable Docker at boot. Attach the instance profile through the EC2 console; do not copy long-lived AWS keys to the instance.

```bash
sudo systemctl enable --now docker
# Allow your deployment user to access Docker, then log out/in:
sudo usermod -aG docker "$USER"
git clone https://github.com/Amitkumarracha/CareerFlowOps.git
cd CareerFlowOps
# Use the full SHA of the successfully published GitHub build:
export RELEASE_SHA='<full-published-git-sha>'
git checkout "$RELEASE_SHA"
python3 infra/scripts/configure.py
# Edit .env locally: production values, distinct tokens, CORS origin, DB password.
nano .env
chmod 600 .env
python3 -m venv .venv-deploy
.venv-deploy/bin/pip install -r requirements-deploy.lock
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export MODEL_BUCKET="careerflowops-models-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export DVC_REMOTE_URL="s3://$MODEL_BUCKET/careerflowops"
export API_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/careerflowops-api:$RELEASE_SHA"
export WEB_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/careerflowops-web:$RELEASE_SHA"
bash infra/aws/deploy.sh
```

Set `CORS_ORIGINS=https://<your-domain>` and `APP_ENV=production` in `.env`. Leave `MODEL_BUNDLE_PATH` to the production Compose overlay. This remains one authenticated candidate identity; add real per-user identity/roles before sharing candidate access with multiple people. The default image runs as UID 1000: make sure `data/` and `mlflow-data/` are writable by that UID and model files are readable, particularly if your deployment user has a different UID. Never change ownership of unrelated host directories.

Deploy checks both image tags against the checkout SHA, pulls ECR images and the DVC model, validates the model with the actual API image, starts/migrates services, then compares the running `/ready` bundle ID with the downloaded manifest. Missing/corrupt/incompatible models fail deployment without a local inference fallback. Validation is cached for a read-only release within each API process; restart the API after replacing a bundle. This is a single-host deployment with possible downtime and no automatic database-migration rollback. Back up PostgreSQL and private data before upgrades. Preserve a previous checkout/image/DVC revision for rollback; assess migration compatibility before using it.

## 6. Public TLS and monitoring

Point your DNS A record at the EC2 address and build the frontend with the same HTTPS origin. Then:

```bash
export PUBLIC_DOMAIN='<your-domain>'
docker compose -f docker-compose.yml -f infra/aws/compose.production.yml -f infra/aws/compose.edge.yml up -d edge
docker compose -f docker-compose.yml -f infra/aws/compose.production.yml --profile monitoring up -d prometheus grafana
curl --fail "https://$PUBLIC_DOMAIN/ready"
docker compose ps
```

Use SSH tunnels for private MLflow/Grafana/Prometheus, not public security-group ports:

```bash
# Workstation; replace the key path and host yourself:
ssh -i '<your-key-file>' -L 5000:127.0.0.1:5000 -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 ubuntu@'<your-ec2-host>'
```

Open the portal's **System & guide** and **Model experiments** pages. Refresh public ATS sources from Source health to populate the fresh database. Upload/review a resume, request a production recommendation, save a job and record an application update. Keep evidence of a successful GitHub run, ECR SHA tags, S3 DVC objects, EC2 readiness with model identity, and a real explained API result for assessment. Container `unless-stopped` policies recover exited containers after daemon restarts; healthchecks report failures but do not automatically restart an unhealthy live process.

References: [DVC S3 remotes](https://doc.dvc.org/user-guide/data-management/remote-storage/amazon-s3), [ECR CLI](https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html), [GitHub OIDC for AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-hardening-deployments/oidc-in-aws), [Docker restart policies](https://docs.docker.com/engine/containers/start-containers-automatically/).
